"""Persistent Chroma collection access. Only ingestion calls write methods."""

from __future__ import annotations

from pathlib import Path
from typing import Any
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


def collection_generation(collection) -> str:
    metadata = collection.metadata or {}
    return str(metadata.get("index_generation", "0"))


def mark_generation(collection) -> str:
    current = collection.metadata or {}
    generation = f"{time.time_ns()}"
    collection.modify(metadata={**current, "index_generation": generation})
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
