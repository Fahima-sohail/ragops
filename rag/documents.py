"""Source loading and page-preserving text extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml


@dataclass
class Document:
    path: Path
    metadata: dict[str, Any]
    pages: list[tuple[int, str]]
    body: str
    sha256: str
    extraction_error: str | None = None

    @property
    def doc_id(self) -> str:
        return str(self.metadata.get("doc_id") or self.path.stem)

    @property
    def doc_version(self) -> str:
        return str(self.metadata.get("version") or self.metadata.get("date") or "unknown")


def _front_matter(text: str) -> tuple[dict[str, Any], str]:
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}, text
    header, sep, body = text[4:].partition("\n---")
    if not sep:
        return {}, text
    metadata = yaml.safe_load(header) or {}
    if not isinstance(metadata, dict):
        return {}, text
    return metadata, body.lstrip("\n")


def _markdown_pages(body: str) -> list[tuple[int, str]]:
    matches = list(re.finditer(r"(?m)^##\s+Page\s+(\d+)\s*$", body, re.IGNORECASE))
    if not matches:
        return [(1, body.strip())]
    pages: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        pages.append((int(match.group(1)), body[match.end():end].strip()))
    return pages


def load_document(path: Path) -> Document:
    import hashlib

    try:
        suffix = path.suffix.lower()
        metadata: dict[str, Any] = {}
        if suffix == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            pdf_meta = reader.metadata or {}
            pages = [(i, (page.extract_text() or "").strip()) for i, page in enumerate(reader.pages, 1)]
            metadata = {
                "title": str(pdf_meta.get("/Title") or "").strip(),
                "source": str(pdf_meta.get("/Author") or path.name).strip(),
                "page_count": len(reader.pages),
                "version": str(pdf_meta.get("/Subject") or "").strip(),
            }
            body = "\n".join(text for _, text in pages)
        else:
            raw_bytes = path.read_bytes()
            text = raw_bytes.decode("utf-8", errors="strict")
            metadata, body = _front_matter(text)
            pages = _markdown_pages(body) if suffix == ".md" else [(1, body.strip())]
        normalized = "\n".join(" ".join(text.split()) for _, text in pages).strip()
        sha256 = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return Document(path, metadata, pages, normalized, sha256)
    except Exception as exc:
        return Document(path, {}, [], "", "", f"{type(exc).__name__}: {exc}")


def discover_documents(root: Path) -> list[Path]:
    excluded = {"quarantine", "archive", "vector_store", "venv", ".venv", "__pycache__"}
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".pdf"}:
            continue
        if any(part.lower() in excluded for part in path.relative_to(root).parts[:-1]):
            continue
        if path.name.startswith(".") or path.name.lower().startswith("readme"):
            continue
        found.append(path)
    return sorted(found, key=lambda item: item.as_posix().casefold())
