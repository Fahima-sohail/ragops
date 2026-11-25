"""Golden question schema, optional human draft loading, and source checks."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from rag.config import ROOT, Settings
from rag.store import open_read_collection

FIELDS = {
    "id", "question", "type", "source", "reviewed", "ground_truth_doc",
    "ground_truth_page", "expected_behavior", "reference_answer",
}
VALID_TYPES = {"answerable", "unanswerable", "hard"}
VALID_BEHAVIORS = {"answer", "abstain"}
_WORD = re.compile(r"[a-z0-9]+", re.I)
_STOP = set("a about an and are as at be by can does for from how in is it of on or that the this to what when where which who with".split())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in {path}:{line_number}: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"golden row in {path}:{line_number} must be an object")
        rows.append(row)
    return rows


def _human_todo_rows(path: Path) -> tuple[list[dict[str, Any]], int]:
    if not path.exists():
        return [], 0
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```jsonl\s*(.*?)\s*```", text, re.S)
    if not match:
        return [], 0
    rows: list[dict[str, Any]] = []
    placeholders = 0
    for line_number, line in enumerate(match.group(1).splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid human JSONL entry at {path}:code-line-{line_number}: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"human draft entry at {path}:code-line-{line_number} must be an object")
        question = str(row.get("question", ""))
        if question.startswith("TODO_HUMAN_QUESTION_"):
            placeholders += 1
            continue
        rows.append(row)
    return rows, placeholders


def validate_row(row: dict[str, Any]) -> None:
    if set(row) != FIELDS:
        raise ValueError(f"golden row {row.get('id', '<no id>')} fields mismatch: missing={sorted(FIELDS-set(row))}, extra={sorted(set(row)-FIELDS)}")
    if row["type"] not in VALID_TYPES:
        raise ValueError(f"{row['id']}: invalid type {row['type']!r}")
    if row["source"] not in {"human", "synthetic"}:
        raise ValueError(f"{row['id']}: source must be human or synthetic")
    if not isinstance(row["reviewed"], bool):
        raise ValueError(f"{row['id']}: reviewed must be boolean")
    if row["expected_behavior"] not in VALID_BEHAVIORS:
        raise ValueError(f"{row['id']}: expected_behavior must be answer or abstain")
    if not str(row["question"]).strip() or not str(row["reference_answer"]).strip():
        raise ValueError(f"{row['id']}: question and reference_answer must be non-empty")
    refs = ground_truth_refs(row)
    if row["expected_behavior"] == "answer" and not refs:
        raise ValueError(f"{row['id']}: answerable items require a document and page")
    if row["expected_behavior"] == "abstain" and refs:
        raise ValueError(f"{row['id']}: abstention items must have null document/page")
    if row["type"] == "unanswerable" and row["expected_behavior"] != "abstain":
        raise ValueError(f"{row['id']}: unanswerable items must expect abstention")


def ground_truth_refs(row: dict[str, Any]) -> list[tuple[str, int]]:
    docs, pages = row.get("ground_truth_doc"), row.get("ground_truth_page")
    if docs is None and pages is None:
        return []
    doc_list = docs if isinstance(docs, list) else [docs]
    page_list = pages if isinstance(pages, list) else [pages]
    if len(doc_list) != len(page_list):
        raise ValueError(f"{row.get('id', '<no id>')}: ground_truth_doc/page list lengths differ")
    return [(str(doc), int(page)) for doc, page in zip(doc_list, page_list)]


def load_golden(path: Path | None = None, include_human_drafts: bool = True) -> tuple[list[dict[str, Any]], dict[str, int]]:
    path = path or ROOT / "eval" / "golden.jsonl"
    rows = _read_jsonl(path)
    if include_human_drafts:
        human_rows, human_placeholders = _human_todo_rows(ROOT / "eval" / "human_questions_todo.md")
    else:
        human_rows, human_placeholders = [], 0
    for row in rows + human_rows:
        validate_row(row)
    identifiers = [str(row["id"]) for row in rows + human_rows]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("golden question ids must be unique, including completed human drafts")
    return rows + human_rows, {
        "base_questions": len(rows),
        "completed_human_drafts": len(human_rows),
        "unfilled_human_placeholders": human_placeholders,
    }


def active_page_texts(settings: Settings) -> dict[tuple[str, int], str]:
    _, collection = open_read_collection(settings)
    rows = collection.get(limit=collection.count(), include=["documents", "metadatas"]) if collection.count() else {"ids": [], "documents": [], "metadatas": []}
    grouped: dict[tuple[str, int], list[tuple[str, str]]] = {}
    for chunk_id, text, metadata in zip(rows["ids"], rows["documents"], rows["metadatas"]):
        if not metadata or metadata.get("status", "active") != "active":
            continue
        key = (str(metadata.get("doc_id", "")), int(metadata.get("page", 1)))
        grouped.setdefault(key, []).append((str(chunk_id), str(text or "")))
    return {key: " ".join(text for _, text in sorted(chunks)) for key, chunks in grouped.items()}


def _normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in _WORD.findall(text) if token.casefold() not in _STOP and len(token) > 2}


def verify_ground_truth(rows: list[dict[str, Any]], page_texts: dict[tuple[str, int], str]) -> list[dict[str, Any]]:
    """Verify every answer reference against indexed active doc/page text."""
    checked: list[dict[str, Any]] = []
    for row in rows:
        refs = ground_truth_refs(row)
        if row["expected_behavior"] == "abstain":
            checked.append({"id": row["id"], "behavior": "abstain", "verified": True, "method": "no_ground_truth_expected"})
            continue
        missing = [f"{doc_id}:p{page}" for doc_id, page in refs if (doc_id, page) not in page_texts]
        if missing:
            raise ValueError(f"{row['id']}: ground-truth pages absent from active collection: {missing}")
        answer = str(row["reference_answer"])
        evidence = " ".join(page_texts[ref] for ref in refs)
        quote_parts = [part.strip() for part in answer.split(" || ") if part.strip()]
        exact = bool(quote_parts) and all(
            any(_normalize(part) in _normalize(page_texts[ref]) for ref in refs)
            for part in quote_parts
        )
        answer_tokens = _tokens(answer)
        evidence_tokens = _tokens(evidence)
        coverage = len(answer_tokens & evidence_tokens) / len(answer_tokens) if answer_tokens else 1.0
        # Curated extractive references should match exactly. For manually authored
        # paraphrases, the disclosed token check still requires most answer terms.
        verified = exact or coverage >= 0.65
        if not verified:
            raise ValueError(f"{row['id']}: reference answer not supported by indexed ground-truth page(s) (token coverage={coverage:.3f})")
        checked.append({
            "id": row["id"],
            "behavior": "answer",
            "verified": True,
            "method": "exact_text" if exact else "token_coverage",
            "token_coverage": round(coverage, 6),
            "ground_truth": [{"doc_id": doc_id, "page": page} for doc_id, page in refs],
        })
    return checked
