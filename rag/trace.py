"""Append-only JSONL query traces and on-demand process metrics."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
from typing import Any


def append_trace(record: dict[str, Any], trace_dir: Path) -> Path:
    trace_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = trace_dir / f"queries_{date}.jsonl"
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    example = trace_dir / "example.jsonl"
    if not example.exists():
        example.write_text(line + "\n", encoding="utf-8")
    return path


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower, upper = int(position), min(int(position) + 1, len(ordered) - 1)
    blend = position - lower
    return ordered[lower] * (1 - blend) + ordered[upper] * blend


def read_traces(trace_dir: Path, since: datetime | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not trace_dir.exists():
        return records
    for path in sorted(trace_dir.glob("queries_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
                stamp = datetime.fromisoformat(str(record["timestamp"]).replace("Z", "+00:00"))
                if since is None or stamp >= since:
                    records.append(record)
            except (ValueError, KeyError, TypeError):
                continue
    return records


def summarize_traces(trace_dir: Path, since: datetime | None = None) -> dict[str, Any]:
    records = read_traces(trace_dir, since)
    top1 = [float(row["retrieved"][0]["score"]) for row in records if row.get("retrieved")]
    latency_keys = ("embed", "retrieve", "rerank", "generate", "total")
    latency = {
        key: {
            "count": len(values := [float(row.get("latency_ms", {}).get(key, 0.0)) for row in records]),
            "p95": round(_percentile(values, 0.95), 3),
        }
        for key in latency_keys
    }
    injection_count = sum(
        1 for row in records
        for action in row.get("guardrail_actions", [])
        if "injection_blocked" in str(action) or "injection_attempt" in str(action)
    )
    count = len(records)
    cache_hits = sum(bool(row.get("cache_hit")) for row in records)
    abstentions = sum(
        1 for row in records
        if not row.get("citations") or "does not provide enough information" in str(row.get("response", "")).lower()
    )
    return {
        "trace_count": count,
        "top1_similarity_distribution": {
            "count": len(top1),
            "mean": round(statistics.fmean(top1), 6) if top1 else None,
            "p50": round(_percentile(top1, 0.5), 6) if top1 else None,
            "p95": round(_percentile(top1, 0.95), 6) if top1 else None,
            "min": round(min(top1), 6) if top1 else None,
            "max": round(max(top1), 6) if top1 else None,
        },
        "abstention_rate": abstentions / count if count else 0.0,
        "cache_hit_rate": cache_hits / count if count else 0.0,
        "p95_latency_ms": latency,
        "injection_attempts_flagged": injection_count,
    }
