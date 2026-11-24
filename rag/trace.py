"""Append-only JSONL query traces and on-demand process metrics."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import threading
from typing import Any

TRACE_FIELDS = {
    "trace_id", "timestamp", "user_query", "rewritten_query", "embedding_model", "embedding_version",
    "collection", "retrieved", "filters", "reranked_order", "prompt_hash", "prompt", "model", "params",
    "response", "citations", "guardrail_actions", "latency_ms", "cache_hit",
}
RETRIEVED_FIELDS = {"chunk_id", "doc_id", "doc_version", "score"}
GUARDRAIL_ACTION_FIELDS = {"rule_name", "chunk_id", "doc_id", "action_taken"}
LATENCY_FIELDS = {"embed", "retrieve", "rerank", "generate", "total"}
_TRACE_LOCK = threading.Lock()


def append_trace(record: dict[str, Any], trace_dir: Path) -> Path:
    if set(record) != TRACE_FIELDS:
        missing = sorted(TRACE_FIELDS - set(record))
        extra = sorted(set(record) - TRACE_FIELDS)
        raise ValueError(f"trace schema mismatch; missing={missing}, extra={extra}")
    if any(set(item) != RETRIEVED_FIELDS for item in record["retrieved"]):
        raise ValueError("retrieved trace entries must contain chunk_id, doc_id, doc_version, and score")
    if any(set(item) != GUARDRAIL_ACTION_FIELDS for item in record["guardrail_actions"]):
        raise ValueError("guardrail actions must contain rule_name, chunk_id, doc_id, and action_taken")
    if set(record["latency_ms"]) != LATENCY_FIELDS:
        raise ValueError("latency_ms must contain embed, retrieve, rerank, generate, and total")
    trace_dir.mkdir(parents=True, exist_ok=True)
    path = trace_dir / "traces.jsonl"
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with _TRACE_LOCK:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
            handle.flush()
        print(line, flush=True)
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
    paths = {trace_dir / "traces.jsonl", *trace_dir.glob("queries_*.jsonl")}
    for path in sorted(paths):
        if not path.is_file():
            continue
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
    flagged_chunks = {
        (str(action.get("doc_id", "")), str(action.get("chunk_id", "")))
        for row in records
        for action in row.get("guardrail_actions", [])
        if isinstance(action, dict) and action.get("action_taken") in {"removed", "neutralized"} and action.get("chunk_id")
    }
    injection_count = len(flagged_chunks)
    injection_count += sum(
        1 for row in records
        for action in row.get("guardrail_actions", [])
        if isinstance(action, str) and ("injection_blocked" in action or "injection_attempt" in action)
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
