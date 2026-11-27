"""Summarize persisted RAG query metrics over a requested time window."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from rag.config import get_settings
from rag.trace import summarize_traces


def parse_since(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use an ISO timestamp or a duration such as 24h") from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("ISO timestamps must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    window = parser.add_mutually_exclusive_group()
    window.add_argument("--since", type=parse_since, help="ISO timestamp with timezone")
    window.add_argument("--last-hours", type=float, help="include records from the last N hours")
    parser.add_argument("--trace-dir", type=Path, help="defaults to TRACE_DIR")
    args = parser.parse_args(argv)
    if args.last_hours is not None and args.last_hours <= 0:
        parser.error("--last-hours must be positive")
    since = args.since
    if args.last_hours is not None:
        since = datetime.now(timezone.utc) - timedelta(hours=args.last_hours)
    result = summarize_traces(args.trace_dir or get_settings().trace_dir, since)
    result["window_start"] = since.isoformat() if since else "all available traces"
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
