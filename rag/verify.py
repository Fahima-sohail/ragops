"""A1 document checks: quality, completeness, recency, and uniqueness."""

from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

from rag.documents import Document
from rag.embeddings import cosine, embed_texts
from rag.config import Settings


def version_key(value: str) -> tuple[int, ...] | None:
    numbers = re.findall(r"\d+", value)
    return tuple(int(number) for number in numbers) if numbers else None


def _existing_docs(rows: dict[str, Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"texts": [], "metadatas": []})
    for text, metadata in zip(rows.get("documents", []), rows.get("metadatas", [])):
        if not metadata:
            continue
        item = grouped[str(metadata.get("doc_id", ""))]
        item["texts"].append(text or "")
        item["metadatas"].append(metadata)
    return dict(grouped)


def verify_batch(documents: list[Document], rows: dict[str, Any], settings: Settings) -> list[dict[str, Any]]:
    existing = _existing_docs(rows)
    existing_hash_to_id: dict[str, str] = {}
    existing_texts: dict[str, str] = {}
    for doc_id, record in existing.items():
        metadata = record["metadatas"]
        active = [value for value in metadata if not bool(value.get("superseded", False))]
        if active:
            existing_hash_to_id[str(active[0].get("doc_sha256", ""))] = doc_id
            existing_texts[doc_id] = "\n".join(record["texts"])

    batch_hash_to_id: dict[str, str] = {}
    valid_for_similarity: list[Document] = []
    outcomes: list[dict[str, Any]] = []

    for doc in documents:
        metadata = doc.metadata
        reasons: dict[str, str] = {}
        checks: dict[str, bool] = {}

        readable = sum(char.isprintable() or char in "\n\t\r" for char in doc.body)
        odd = sum(not (char.isprintable() or char in "\n\t\r") for char in doc.body)
        quality_ok = bool(doc.body.strip()) and len(doc.body.strip()) >= 40 and odd <= max(2, readable * 0.02)
        if doc.extraction_error:
            quality_ok = False
            reasons["quality"] = f"extraction failed: {doc.extraction_error}"
        elif not doc.body.strip():
            reasons["quality"] = "extracted text is empty"
        elif len(doc.body.strip()) < 40:
            reasons["quality"] = "extracted text is too short to be usable"
        elif not quality_ok:
            reasons["quality"] = "extracted text contains too many non-printing characters"
        else:
            reasons["quality"] = "readable extracted text"
        checks["quality"] = quality_ok

        missing = [name for name in ("source", "title") if not str(metadata.get(name, "")).strip()]
        if not str(metadata.get("version", "")).strip() and not str(metadata.get("date", "")).strip():
            missing.append("date or version")
        try:
            declared_pages = int(metadata.get("page_count", 0))
        except (TypeError, ValueError):
            declared_pages = 0
        if declared_pages <= 0:
            missing.append("page_count")
        elif doc.pages and declared_pages != len(doc.pages):
            missing.append(f"page_count mismatch (declared {declared_pages}, extracted {len(doc.pages)})")
        truncated = bool(metadata.get("truncated", False)) or "[TRUNCATED]" in doc.body.upper()
        if truncated:
            missing.append("text is marked truncated")
        complete = not missing
        reasons["completeness"] = "all required metadata and complete text are present" if complete else "missing or incomplete: " + ", ".join(missing)
        checks["completeness"] = complete

        doc_id = doc.doc_id
        version = doc.doc_version
        active_versions = [
            str(value.get("doc_version", "unknown"))
            for value in existing.get(doc_id, {}).get("metadatas", [])
            if not bool(value.get("superseded", False))
        ]
        current_version = active_versions[0] if active_versions else None
        candidate_key, current_key = version_key(version), version_key(current_version or "")
        if current_version and candidate_key and current_key and candidate_key < current_key:
            recency_ok = False
            reasons["recency"] = f"candidate {version} is older than active {current_version}"
        elif current_version and version != current_version:
            recency_ok = True
            reasons["recency"] = f"newer version {version} detected; prior {current_version} will be archived and superseded"
        elif current_version:
            reasons["recency"] = f"version {version} matches the active record"
            recency_ok = True
        else:
            reasons["recency"] = "no prior active version for this document id"
            recency_ok = True
        checks["recency"] = recency_ok

        exact_other = existing_hash_to_id.get(doc.sha256) if doc.sha256 else None
        batch_other = batch_hash_to_id.get(doc.sha256) if doc.sha256 else None
        if exact_other and exact_other != doc_id:
            unique_ok = False
            reasons["uniqueness"] = f"exact duplicate of existing document {exact_other} by SHA-256"
        elif batch_other and batch_other != doc_id:
            unique_ok = False
            reasons["uniqueness"] = f"exact duplicate of batch document {batch_other} by SHA-256"
        elif doc.sha256:
            batch_hash_to_id.setdefault(doc.sha256, doc_id)
            reasons["uniqueness"] = "no exact duplicate detected; near-duplicate check pending"
            unique_ok = True
            valid_for_similarity.append(doc)
        else:
            unique_ok = False
            reasons["uniqueness"] = "cannot calculate a content hash"
        checks["uniqueness"] = unique_ok

        outcomes.append({
            "doc_id": doc_id,
            "path": str(doc.path),
            "title": str(metadata.get("title", "")),
            "doc_version": version,
            "sha256": doc.sha256,
            "checks": checks,
            "reasons": reasons,
            "supersedes_version": current_version if current_version and version != current_version else None,
            "passed": all(checks.values()),
        })

    # The whole-document embedding check is deterministic and uses the same local
    # model as chunk embedding. Same-id revisions are intentionally exempt because
    # their similarity is expected and their version is checked above.
    candidates = [item for item in outcomes if item["checks"]["uniqueness"] and item["sha256"]]
    if candidates:
        candidate_docs = [doc for doc in valid_for_similarity if any(item["doc_id"] == doc.doc_id and item["sha256"] == doc.sha256 for item in candidates)]
        vectors, _ = embed_texts([doc.body for doc in candidate_docs], settings.embed_model, settings.local_device)
        candidate_vector = {doc.doc_id: vector for doc, vector in zip(candidate_docs, vectors)}
        active_existing = [(doc_id, text) for doc_id, text in existing_texts.items()]
        similarity_texts = [text for _, text in active_existing]
        if similarity_texts:
            existing_vectors, _ = embed_texts(similarity_texts, settings.embed_model, settings.local_device)
            existing_vector = {doc_id: vector for (doc_id, _), vector in zip(active_existing, existing_vectors)}
        else:
            existing_vector = {}

        accepted_vectors: dict[str, list[float]] = dict(existing_vector)
        for item in outcomes:
            if item["doc_id"] not in candidate_vector or not item["checks"]["uniqueness"]:
                continue
            vector = candidate_vector[item["doc_id"]]
            similarities = [
                (other_id, cosine(vector, other_vector))
                for other_id, other_vector in accepted_vectors.items()
                if other_id != item["doc_id"]
            ]
            if similarities:
                other_id, score = max(similarities, key=lambda pair: pair[1])
                item["near_duplicate_score"] = round(score, 6)
                item["near_duplicate_match"] = other_id
                if score >= settings.near_duplicate_threshold:
                    item["checks"]["uniqueness"] = False
                    item["reasons"]["uniqueness"] = f"near duplicate of {other_id}: cosine={score:.4f} >= {settings.near_duplicate_threshold:.2f}"
            if item["checks"]["uniqueness"]:
                accepted_vectors[item["doc_id"]] = vector
            item["passed"] = all(item["checks"].values())

    return outcomes
