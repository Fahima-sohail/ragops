"""Verify, update, archive, chunk, embed, and persist a document batch."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys
import time
from typing import Any

from rag.chunking import make_chunks
from rag.config import ROOT, get_settings
from rag.documents import Document, discover_documents, load_document
from rag.embeddings import embed_texts
from rag.store import (
    collection_rows,
    mark_generation,
    open_collection,
    open_read_collection,
    remove_ids,
    update_metadata,
    upsert_chunks,
    write_manifest,
)
from rag.verify import verify_batch


def _safe_component(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._") or "document"


def _active_metadata(rows: dict[str, Any], doc_id: str) -> list[tuple[str, dict[str, Any]]]:
    return [
        (chunk_id, metadata)
        for chunk_id, metadata in zip(rows.get("ids", []), rows.get("metadatas", []))
        if metadata
        and metadata.get("doc_id") == doc_id
        and str(metadata.get("status", "archived" if metadata.get("superseded", False) else "active")) == "active"
    ]


def _doc_rows(collection, doc_id: str) -> dict[str, Any]:
    return collection.get(where={"doc_id": doc_id}, include=["metadatas", "documents"])


def _archive_active(collection, settings, doc_id: str, report: dict[str, Any]) -> None:
    rows = _doc_rows(collection, doc_id)
    active = _active_metadata(rows, doc_id)
    if not active:
        return
    for _, metadata in active:
        source = Path(str(metadata.get("source_path", "")))
        version = str(metadata.get("doc_version", "unknown"))
        if source.is_file() and settings.archive_dir not in source.parents:
            destination_dir = settings.archive_dir / _safe_component(doc_id)
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination = destination_dir / f"{_safe_component(version)}__{source.name}"
            if not destination.exists():
                shutil.copy2(source, destination)
            if not any(item.get("doc_id") == doc_id and item.get("version") == version for item in report.setdefault("archived_versions", [])):
                report["archived_versions"].append({
                    "doc_id": doc_id,
                    "version": version,
                    "path": str(destination),
                })
    ids = [chunk_id for chunk_id, _ in active]
    metadata = [dict(old, status="archived", superseded=True) for _, old in active]
    update_metadata(collection, ids, metadata)


def _move_to_quarantine(document: Document, settings, run_id: str, outcome: dict[str, Any]) -> str:
    destination_dir = settings.quarantine_dir / run_id
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / document.path.name
    if destination.exists():
        destination = destination_dir / f"{document.path.stem}-{document.sha256[:8]}{document.path.suffix}"
    if document.path.exists():
        shutil.move(str(document.path), str(destination))
    sidecar = destination.with_suffix(destination.suffix + ".verification.json")
    sidecar.write_text(json.dumps(outcome, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(destination)


def _write_report(report: dict[str, Any]) -> Path:
    results_dir = ROOT / "eval" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / f"verification_{report['run_id']}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _restore(collection, settings, doc_id: str, version: str) -> dict[str, Any]:
    target: Path | None = None
    for path in settings.archive_dir.rglob("*") if settings.archive_dir.exists() else []:
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".pdf"}:
            continue
        document = load_document(path)
        if document.doc_id == doc_id and document.doc_version == version:
            target = path
            break
    if target is None:
        raise FileNotFoundError(f"archived source for {doc_id} version {version} was not found")

    rows = _doc_rows(collection, doc_id)
    target_ids = [
        chunk_id for chunk_id, metadata in zip(rows.get("ids", []), rows.get("metadatas", []))
        if metadata and str(metadata.get("doc_version")) == version
    ]
    if target_ids:
        updated = []
        for metadata in rows["metadatas"]:
            copied = dict(metadata)
            is_target = str(copied.get("doc_version")) == version
            copied["status"] = "active" if is_target else "archived"
            copied["superseded"] = not is_target
            if is_target:
                copied["source_path"] = str(target)
            updated.append(copied)
        update_metadata(collection, list(rows["ids"]), updated)
        generation = mark_generation(collection, settings.vector_dir)
        return {
            "restored": True,
            "doc_id": doc_id,
            "version": version,
            "embedded_chunks": 0,
            "reactivated_chunks": len(target_ids),
            "index_generation": generation,
            "source": str(target),
        }

    document = load_document(target)
    outcome = verify_batch([document], collection_rows(collection), settings)[0]
    # An explicit rollback may select an older archived revision. Its age is the
    # purpose of the operation; all other verification checks still apply.
    outcome["checks"]["recency"] = True
    outcome["reasons"]["recency"] = "explicit rollback to archived version"
    outcome["passed"] = all(outcome["checks"].values())
    if not outcome["passed"]:
        raise ValueError(f"archived source failed verification: {outcome['reasons']}")
    return _ingest_valid(collection, settings, [document], [outcome], Path("."), rollback=True)


def _ingest_valid(collection, settings, documents: list[Document], outcomes: list[dict[str, Any]], source_root: Path, rollback: bool = False) -> dict[str, Any]:
    report: dict[str, Any] = {
        "indexed_docs": 0,
        "added_chunks": 0,
        "replaced_chunks": 0,
        "embedded_chunks": 0,
        "skipped_unchanged_chunks": 0,
        "deleted_chunks": 0,
        "new_docs": 0,
        "updated_docs": 0,
        "unchanged_docs": 0,
        "deleted_docs": 0,
        "new_chunks": 0,
        "updated_chunks": 0,
        "unchanged_chunks": 0,
        "archived_versions": [],
        "by_doc_id": {},
    }

    def doc_counts(doc_id: str) -> dict[str, int]:
        return report["by_doc_id"].setdefault(doc_id, {
            "added_chunks": 0,
            "replaced_chunks": 0,
            "skipped_unchanged_chunks": 0,
            "deleted_chunks": 0,
        })

    to_write: list[tuple[Document, list[Any], list[str], list[dict[str, Any]]]] = []
    for document, outcome in zip(documents, outcomes):
        if not outcome["passed"]:
            continue
        doc_id, version, digest = document.doc_id, document.doc_version, document.sha256
        current = _doc_rows(collection, doc_id)
        current_ids = list(current.get("ids", []))
        current_metadata = list(current.get("metadatas", []))
        exact_version = [
            index for index, metadata in enumerate(current_metadata)
            if metadata and str(metadata.get("doc_version")) == version
        ]
        exact_unchanged = [
            index for index in exact_version
            if str(current_metadata[index].get("doc_sha256", "")) == digest
        ]
        if exact_unchanged and len(exact_unchanged) == len(exact_version) and not rollback:
            report["unchanged_docs"] += 1
            report["unchanged_chunks"] += len(exact_unchanged)
            report["skipped_unchanged_chunks"] += len(exact_unchanged)
            doc_counts(doc_id)["skipped_unchanged_chunks"] += len(exact_unchanged)
            continue

        active_versions = {str(meta.get("doc_version")) for _, meta in _active_metadata(current, doc_id)}
        incoming_key = tuple(int(x) for x in re.findall(r"\d+", version))
        for active_version in active_versions:
            active_key = tuple(int(x) for x in re.findall(r"\d+", active_version))
            if rollback or (incoming_key and active_key and incoming_key != active_key):
                _archive_active(collection, settings, doc_id, report)
                break

        # A same-version content update replaces only that version's own chunks.
        current = _doc_rows(collection, doc_id)
        is_new_document = not current.get("ids")
        same_version_ids = [
            chunk_id for chunk_id, metadata in zip(current.get("ids", []), current.get("metadatas", []))
            if metadata and str(metadata.get("doc_version")) == version
        ]
        if same_version_ids and not rollback:
            report["deleted_chunks"] += len(same_version_ids)
            report["replaced_chunks"] += len(same_version_ids)
            doc_counts(doc_id)["replaced_chunks"] += len(same_version_ids)
            doc_counts(doc_id)["deleted_chunks"] += len(same_version_ids)
            remove_ids(collection, same_version_ids)

        chunks = make_chunks(document, settings.chunk_size, settings.chunk_overlap)
        ids = [chunk.chunk_id for chunk in chunks]
        metadatas = []
        for chunk in chunks:
            meta = {
                "doc_id": chunk.doc_id,
                "doc_version": chunk.doc_version,
                "doc_sha256": digest,
                "source": str(document.metadata.get("source", document.path.name)),
                "title": chunk.title,
                "page": int(chunk.page),
                "status": "active",
                "superseded": False,
                "source_path": str(document.path.resolve()),
                "source_root": str(source_root.resolve()),
            }
            metadatas.append(meta)
        to_write.append((document, chunks, ids, metadatas))
        report["indexed_docs"] += 1
        if is_new_document:
            report["new_docs"] += 1
            report["new_chunks"] += len(chunks)
        else:
            report["updated_docs"] += 1
            report["updated_chunks"] += len(chunks)

    flat_chunks = [chunk for _, chunks, _, _ in to_write for chunk in chunks]
    vectors, embed_ms = embed_texts([chunk.text for chunk in flat_chunks], settings.embed_model, settings.local_device)
    report["embedded_chunks"] = len(flat_chunks)
    report["embedding_ms"] = round(embed_ms, 3)
    report["added_chunks"] = sum(len(chunks) for _, chunks, _, _ in to_write)
    for document, chunks, ids, metadatas in to_write:
        start = report.setdefault("_embedding_cursor", 0)
        end = start + len(chunks)
        upsert_chunks(
            collection,
            ids,
            [chunk.text for chunk in chunks],
            metadatas,
            vectors[start:end],
        )
        report["_embedding_cursor"] = end
        doc_counts(document.doc_id)["added_chunks"] += len(chunks)
    report.pop("_embedding_cursor", None)
    return report


def ingest(data_dir: Path, collection_name: str, sync: bool = False, restore_doc: str | None = None, restore_version: str | None = None) -> dict[str, Any]:
    settings = get_settings(collection=collection_name)
    started = time.perf_counter()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{time.time_ns() % 1_000_000:06d}"
    _, collection = open_collection(settings, collection_name)

    if restore_doc:
        if not restore_version:
            raise ValueError("--restore requires a document id and version")
        summary = _restore(collection, settings, restore_doc, restore_version)
        manifest = write_manifest(collection, settings.vector_dir)
        summary["manifest_path"] = str(manifest)
        report = {"run_id": run_id, "timestamp": datetime.now(timezone.utc).isoformat(), "collection": collection_name, **summary}
        report_path = _write_report(report)
        report["report_path"] = str(report_path)
        report["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
        print(
            f"restore collection={collection_name} doc_id={restore_doc} version={restore_version} "
            f"reactivated_chunks={summary.get('reactivated_chunks', summary.get('added_chunks', 0))} "
            f"embedded_chunks={summary.get('embedded_chunks', 0)} report={report_path} manifest={manifest}"
        )
        return report

    paths = discover_documents(data_dir)
    if not paths:
        raise FileNotFoundError(f"no .md, .txt, or .pdf documents found under {data_dir}")
    documents = [load_document(path) for path in paths]
    old_rows = collection_rows(collection)
    outcomes = verify_batch(documents, old_rows, settings)
    passed_docs = [doc for doc, outcome in zip(documents, outcomes) if outcome["passed"]]
    passed_outcomes = [outcome for outcome in outcomes if outcome["passed"]]
    summary = _ingest_valid(collection, settings, passed_docs, passed_outcomes, data_dir)

    moved: list[dict[str, str]] = []
    for document, outcome in zip(documents, outcomes):
        if not outcome["passed"]:
            outcome["quarantine_path"] = _move_to_quarantine(document, settings, run_id, outcome)
            moved.append({"doc_id": document.doc_id, "path": outcome["quarantine_path"]})

    deleted_ids: list[str] = []
    deleted_by_doc: dict[str, int] = {}
    if sync:
        discovered_ids = {document.doc_id for document in documents}
        rows = collection_rows(collection)
        for chunk_id, metadata in zip(rows.get("ids", []), rows.get("metadatas", [])):
            if metadata and str(metadata.get("doc_id")) not in discovered_ids:
                deleted_ids.append(chunk_id)
                doc_id = str(metadata.get("doc_id", "unknown"))
                deleted_by_doc[doc_id] = deleted_by_doc.get(doc_id, 0) + 1
        remove_ids(collection, deleted_ids)
        summary["deleted_chunks"] += len(deleted_ids)
        summary["deleted_docs"] = len(deleted_by_doc)
        for doc_id, count in deleted_by_doc.items():
            per_doc = summary["by_doc_id"].setdefault(doc_id, {
                "added_chunks": 0,
                "replaced_chunks": 0,
                "skipped_unchanged_chunks": 0,
                "deleted_chunks": 0,
            })
            per_doc["deleted_chunks"] += count

    if summary.get("added_chunks") or summary.get("deleted_chunks") or moved:
        summary["index_generation"] = mark_generation(collection, settings.vector_dir)
    manifest = write_manifest(collection, settings.vector_dir)

    report = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_dir": str(data_dir.resolve()),
        "collection": collection_name,
        "verification": outcomes,
        "counts": {
            "discovered_docs": len(documents),
            "passed_docs": len(passed_docs),
            "quarantined_docs": len(moved),
            **summary,
        },
        "quarantine": moved,
        "deleted_chunks_by_doc_id": deleted_by_doc,
        "manifest_path": str(manifest),
    }
    report_path = _write_report(report)
    report["report_path"] = str(report_path)
    report["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    print(
        f"ingest collection={collection_name} "
        f"new_docs={summary['new_docs']} updated_docs={summary['updated_docs']} "
        f"unchanged_docs={summary['unchanged_docs']} deleted_docs={summary['deleted_docs']} "
        f"new_chunks={summary['new_chunks']} updated_chunks={summary['updated_chunks']} "
        f"unchanged_chunks={summary['unchanged_chunks']} deleted_chunks={summary['deleted_chunks']} "
        f"embedded_chunks={summary['embedded_chunks']} quarantined_docs={len(moved)} "
        f"report={report_path} manifest={manifest}"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Verify and update a persistent Chroma collection.")
    parser.add_argument("--data", default=str(settings.data_dir), help="input snapshot or incremental batch directory")
    parser.add_argument("--collection", default=settings.collection)
    parser.add_argument("--sync", action="store_true", help="delete collection rows absent from this complete snapshot")
    parser.add_argument("--count-by-doc", action="store_true", help="print stored chunk counts grouped by document id")
    parser.add_argument("--doc-id", help="with --count-by-doc, also print this id when its count is zero")
    parser.add_argument("--restore", nargs=2, metavar=("DOC_ID", "VERSION"), help="restore an archived document version")
    args = parser.parse_args(argv)
    try:
        if args.count_by_doc:
            _, collection = open_read_collection(settings, args.collection)
            counts: dict[str, int] = {}
            for metadata in collection_rows(collection).get("metadatas", []):
                if metadata:
                    doc_id = str(metadata.get("doc_id", "unknown"))
                    counts[doc_id] = counts.get(doc_id, 0) + 1
            if args.doc_id:
                counts.setdefault(args.doc_id, 0)
            for doc_id in sorted(counts):
                print(f"{doc_id}: {counts[doc_id]}")
            return 0
        restore_doc, restore_version = args.restore if args.restore else (None, None)
        ingest(Path(args.data).resolve(), args.collection, args.sync, restore_doc, restore_version)
        return 0
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
