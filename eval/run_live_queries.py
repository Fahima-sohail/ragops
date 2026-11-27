"""Send the 40-query simulated live workload to a running RAGOps API."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

import httpx

from rag.config import ROOT


def read_workload(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 40 or len({row["id"] for row in rows}) != len(rows):
        raise ValueError("live workload must contain exactly 40 unique query records")
    if sum(bool(row["expected_domain"]) for row in rows) < 28 or sum(not row["expected_domain"] for row in rows) < 12:
        raise ValueError("live workload must include at least 28 in-domain and 12 out-of-domain queries")
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="base URL of the live API")
    parser.add_argument("--input", type=Path, default=ROOT / "eval" / "live_queries.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "eval" / "results" / "live_query_log.jsonl")
    parser.add_argument("--delay", type=float, default=0.0, help="seconds between requests")
    args = parser.parse_args(argv)
    if args.delay < 0:
        parser.error("--delay must be non-negative")
    try:
        rows = read_workload(args.input)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        records = []
        with httpx.Client(timeout=300.0) as client:
            for row in rows:
                started = time.perf_counter()
                response = client.post(f"{args.url.rstrip('/')}/query", json={"question": row["query"]})
                response.raise_for_status()
                result = response.json()
                records.append({
                    **row,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "trace_id": result.get("trace_id"),
                    "answer": result.get("answer"),
                    "citations": result.get("citations", []),
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                })
                if args.delay:
                    time.sleep(args.delay)
        args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
        print(f"Live queries: {len(records)} ({sum(bool(row['expected_domain']) for row in records)} in-domain, {sum(not row['expected_domain'] for row in records)} out-of-domain)")
        print(f"Query log: {args.output}")
        print(f"Trace IDs recorded: {sum(bool(row['trace_id']) for row in records)}")
        return 0
    except (OSError, ValueError, httpx.HTTPError, KeyError) as exc:
        print(f"live query run failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
