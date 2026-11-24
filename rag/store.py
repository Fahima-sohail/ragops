"""Persistent Chroma collection access. Only ingestion calls write methods."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os
import time

import chromadb
from chromadb.config import Settings as ChromaSettings

from rag.config import Settings


def open_collection(settings: Settings, name: str | None = None):
    settings.vector_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(settings.vector_dir),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection_name = name or settings.collection
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine", "owner": "rag.ingest"},
    )
    return client, collection


def open_read_collection(settings: Settings, name: str | None = None):
    """Open an existing collection without collection creation or vector writes."""
    if not settings.vector_dir.is_dir() or not (settings.vector_dir / "chroma.sqlite3").is_file():
        raise FileNotFoundError(f"Chroma persistence directory is not initialized: {settings.vector_dir}")
    client = chromadb.PersistentClient(
        path=str(settings.vector_dir),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection = client.get_collection(name=name or settings.collection)
    return client, collection


def collection_rows(collection) -> dict[str, Any]:
    count = collection.count()
    if not count:
        return {"ids": [], "documents": [], "metadatas": [], "embeddings": []}
    return collection.get(
        limit=count,
        include=["documents", "metadatas", "embeddings"],
    )


def count_by_doc(collection, doc_id: str) -> int:
    rows = collection.get(where={"doc_id": doc_id}, include=["metadatas"])
    return len(rows.get("ids", []))


def manifest_path(vector_dir: Path, collection_name: str) -> Path:
    """Return the per-collection document manifest beside Chroma's database."""
    return vector_dir / f"{collection_name}.manifest.json"


def write_manifest(collection, vector_dir: Path) -> Path:
    """Persist document versions and their chunk ids from the current collection."""
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    count = collection.count()
    rows = collection.get(limit=count, include=["metadatas"]) if count else {"ids": [], "metadatas": []}
    for chunk_id, metadata in zip(rows["ids"], rows["metadatas"]):
        if not metadata:
            continue
        doc_id = str(metadata.get("doc_id", ""))
        version = str(metadata.get("doc_version", "unknown"))
        key = (doc_id, version)
        item = grouped.setdefault(key, {
            "doc_id": doc_id,
            "content_hash": str(metadata.get("doc_sha256", "")),
            "version": version,
            "status": str(metadata.get("status", "archived" if metadata.get("superseded", False) else "active")),
            "chunk_ids": [],
        })
        item["chunk_ids"].append(str(chunk_id))
    documents = sorted(grouped.values(), key=lambda item: (item["doc_id"], item["version"]))
    for document in documents:
        document["chunk_ids"].sort()
    target = manifest_path(vector_dir, collection.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    payload = {
        "collection": collection.name,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "documents": documents,
    }
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, target)
    return target


def collection_generation(collection, vector_dir: Path | None = None) -> str:
    metadata = collection.metadata or {}
    if vector_dir is not None:
        marker = vector_dir / ".generation" / f"{collection.name}.txt"
        if marker.is_file():
            return marker.read_text(encoding="utf-8").strip() or "0"
    return str(metadata.get("index_generation", "0"))


def mark_generation(collection, vector_dir: Path) -> str:
    generation = f"{time.time_ns()}"
    marker_dir = vector_dir / ".generation"
    marker_dir.mkdir(parents=True, exist_ok=True)
    (marker_dir / f"{collection.name}.txt").write_text(generation, encoding="utf-8")
    return generation


def update_metadata(collection, ids: list[str], metadata: list[dict[str, Any]]) -> None:
    if ids:
        collection.update(ids=ids, metadatas=metadata)


def remove_ids(collection, ids: list[str]) -> None:
    if ids:
        collection.delete(ids=ids)


def upsert_chunks(collection, ids, documents, metadatas, embeddings) -> None:
    if ids:
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
