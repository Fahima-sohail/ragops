"""Read-only Chroma retrieval with explicit active-version filtering."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from rag.config import Settings
from rag.embeddings import embed_texts
from rag.store import open_read_collection


@dataclass
class Passage:
    chunk_id: str
    doc_id: str
    doc_version: str
    title: str
    source: str
    page: int
    score: float
    text: str

    def citation(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "doc_version": self.doc_version,
            "title": self.title,
            "source": self.source,
            "page": self.page,
            "chunk_id": self.chunk_id,
        }


def retrieve(query: str, settings: Settings, top_k: int | None = None) -> tuple[list[Passage], float, float, list[float]]:
    _, collection = open_read_collection(settings)
    vector_list, embed_ms = embed_texts([query], settings.embed_model, settings.local_device)
    vector = vector_list[0]
    started = time.perf_counter()
    count = collection.count()
    if count == 0:
        return [], embed_ms, 0.0, vector
    result = collection.query(
        query_embeddings=[vector],
        n_results=min(top_k or settings.top_k, count),
        where={"status": "active"},
        include=["documents", "metadatas", "distances"],
    )
    retrieve_ms = (time.perf_counter() - started) * 1000.0
    passages: list[Passage] = []
    for chunk_id, text, metadata, distance in zip(
        result.get("ids", [[]])[0],
        result.get("documents", [[]])[0],
        result.get("metadatas", [[]])[0],
        result.get("distances", [[]])[0],
    ):
        score = max(-1.0, min(1.0, 1.0 - float(distance)))
        passages.append(Passage(
            chunk_id=str(chunk_id),
            doc_id=str(metadata.get("doc_id", "")),
            doc_version=str(metadata.get("doc_version", "unknown")),
            title=str(metadata.get("title", "")),
            source=str(metadata.get("source", "")),
            page=int(metadata.get("page", 0)),
            score=score,
            text=str(text or ""),
        ))
    return passages, embed_ms, retrieve_ms, vector
