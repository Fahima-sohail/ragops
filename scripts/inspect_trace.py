"""Print the exact prompt and retrieved context for a persisted query trace."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rag.config import get_settings
from rag.store import open_read_collection


def find_trace(trace_id: str, trace_file: Path) -> dict:
    if not trace_file.is_file():
        raise FileNotFoundError(f"trace file not found: {trace_file}")
    matches = []
    for number, line in enumerate(trace_file.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at {trace_file}:{number}: {exc.msg}") from exc
        if row.get("trace_id") == trace_id:
            matches.append(row)
    if not matches:
        raise KeyError(f"trace id not found: {trace_id}")
    if len(matches) > 1:
        raise ValueError(f"trace id is not unique: {trace_id}")
    return matches[0]


def inspect(trace_id: str, trace_file: Path, settings=None) -> str:
    row = find_trace(trace_id, trace_file)
    settings = settings or get_settings()
    _, collection = open_read_collection(settings, name=str(row["collection"]))
    chunks = [item["chunk_id"] for item in row.get("retrieved", [])]
    records = collection.get(ids=chunks, include=["documents", "metadatas"]) if chunks else {"ids": [], "documents": [], "metadatas": []}
    by_id = {
        chunk_id: (text or "", metadata or {})
        for chunk_id, text, metadata in zip(records.get("ids", []), records.get("documents", []), records.get("metadatas", []))
    }
    output = [f"Trace: {trace_id}", f"Collection: {row['collection']}", "", "PROMPT", row.get("prompt", ""), "", "RETRIEVED CONTEXT"]
    for rank, item in enumerate(row.get("retrieved", []), 1):
        chunk_id = str(item["chunk_id"])
        if chunk_id not in by_id:
            raise KeyError(f"retrieved chunk no longer exists in collection {row['collection']}: {chunk_id}")
        text, metadata = by_id[chunk_id]
        expected_doc = str(item.get("doc_id", ""))
        expected_version = str(item.get("doc_version", ""))
        if str(metadata.get("doc_id", "")) != expected_doc or str(metadata.get("doc_version", "")) != expected_version:
            raise ValueError(f"stored metadata changed for trace chunk {chunk_id}")
        output.extend((
            "",
            f"[{rank}] chunk_id={chunk_id} doc_id={expected_doc} version={expected_version} score={item.get('score')}",
            text,
        ))
    return "\n".join(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace_id")
    parser.add_argument("--file", type=Path, help="JSONL trace file (defaults to TRACE_DIR/traces.jsonl)")
    args = parser.parse_args(argv)
    try:
        trace_file = args.file or (get_settings().trace_dir / "traces.jsonl")
        print(inspect(args.trace_id, trace_file))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"trace inspection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
