"""Stable, page-aware whitespace-token chunking."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any

from rag.documents import Document


@dataclass
class Chunk:
    chunk_id: str
    text: str
    doc_id: str
    doc_version: str
    page: int
    title: str
    metadata: dict[str, Any]


def make_chunks(document: Document, size: int, overlap: int) -> list[Chunk]:
    if size < 1 or not 0 <= overlap < size:
        raise ValueError("CHUNK_SIZE must be positive and CHUNK_OVERLAP smaller than it")
    chunks: list[Chunk] = []
    for page_number, page_text in document.pages:
        words = page_text.split()
        start = 0
        while start < len(words):
            end = min(start + size, len(words))
            text = " ".join(words[start:end]).strip()
            if text:
                number = len(chunks) + 1
                digest = hashlib.sha256(f"{document.doc_id}\0{document.doc_version}\0{page_number}\0{number}\0{text}".encode("utf-8")).hexdigest()[:16]
                chunks.append(Chunk(
                    chunk_id=f"{document.doc_id}-{document.doc_version}-{number:04d}-{digest}",
                    text=text,
                    doc_id=document.doc_id,
                    doc_version=document.doc_version,
                    page=page_number,
                    title=str(document.metadata.get("title", document.path.stem)),
                    metadata=document.metadata,
                ))
            if end >= len(words):
                break
            start = end - overlap
    return chunks
