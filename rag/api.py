"""Read-only query API with trace-backed Prometheus metrics."""

from __future__ import annotations

import threading
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import AliasChoices, BaseModel, Field

from rag.config import get_settings
from rag.generate import ABSTENTION, run_query

app = FastAPI(title="RAGOps API", version="1.1.0")
settings = get_settings()

_LATENCY_BUCKETS = (1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000)
_SIMILARITY_BUCKETS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
_LATENCY_STAGES = ("embed", "retrieve", "rerank", "generate", "total")


class QueryRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
        validation_alias=AliasChoices("question", "query"),
    )
    top_k: int | None = Field(default=None, ge=1, le=30)


class _Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.queries_total = 0
        self.abstentions_total = 0
        self.cache_hits_total = 0
        self.injections_flagged_total = 0
        self.latencies: dict[str, list[float]] = {stage: [] for stage in _LATENCY_STAGES}
        self.top1_similarity: list[float] = []

    def record(self, result: dict[str, Any]) -> None:
        actions = result.get("guardrail_actions", [])
        flagged_chunks = {
            (str(action.get("doc_id", "")), str(action.get("chunk_id", "")))
            for action in actions
            if isinstance(action, dict)
            and action.get("action_taken") in {"removed", "neutralized"}
            and action.get("chunk_id")
        }
        retrieved = result.get("retrieved", [])
        top1 = float(retrieved[0].get("score", 0.0)) if retrieved else 0.0
        latency = result.get("latency_ms", {})
        with self._lock:
            self.queries_total += 1
            if result.get("response") == ABSTENTION or not result.get("citations"):
                self.abstentions_total += 1
            if result.get("cache_hit"):
                self.cache_hits_total += 1
            self.injections_flagged_total += len(flagged_chunks)
            self.top1_similarity.append(top1)
            for stage in _LATENCY_STAGES:
                self.latencies[stage].append(float(latency.get(stage, 0.0)))

    @staticmethod
    def _histogram(name: str, help_text: str, observations: list[float], buckets: tuple[float, ...]) -> list[str]:
        lines = [f"# HELP {name} {help_text}", f"# TYPE {name} histogram"]
        for bound in buckets:
            rendered = f"{bound:g}"
            count = sum(value <= bound for value in observations)
            lines.append(f'{name}_bucket{{le="{rendered}"}} {count}')
        lines.extend((
            f'{name}_bucket{{le="+Inf"}} {len(observations)}',
            f"{name}_sum {sum(observations):.6f}",
            f"{name}_count {len(observations)}",
        ))
        return lines

    def render(self) -> str:
        with self._lock:
            counters = (
                ("queries_total", "Total requests handled by the query endpoint.", self.queries_total),
                ("abstentions_total", "Responses abstained for lack of supported evidence.", self.abstentions_total),
                ("cache_hits_total", "Responses served from the in-memory query cache.", self.cache_hits_total),
                ("injections_flagged_total", "Retrieved chunks removed by the prompt-injection rail.", self.injections_flagged_total),
            )
            lines = [
                line
                for name, help_text, value in counters
                for line in (f"# HELP {name} {help_text}", f"# TYPE {name} counter", f"{name} {value}")
            ]
            for stage in _LATENCY_STAGES:
                metric = f"{stage}_latency_ms"
                lines.extend(self._histogram(metric, f"{stage} stage latency in milliseconds.", list(self.latencies[stage]), _LATENCY_BUCKETS))
            lines.extend(self._histogram(
                "top1_similarity",
                "Top retrieved cosine similarity, or zero when no chunks were retrieved.",
                list(self.top1_similarity),
                _SIMILARITY_BUCKETS,
            ))
        return "\n".join(lines) + "\n"


_METRICS = _Metrics()


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "collection": settings.collection, "vector_dir_exists": settings.vector_dir.exists()}


@app.post("/query")
def query(request: QueryRequest) -> dict[str, Any]:
    try:
        result = run_query(request.question, settings=settings, top_k=request.top_k)
        _METRICS.record(result)
        return {
            "trace_id": result["trace_id"],
            "answer": result["response"],
            "citations": result["citations"],
            "guardrail_actions": result["guardrail_actions"],
            "cache_hit": result["cache_hit"],
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"query pipeline unavailable: {type(exc).__name__}") from exc


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(content=_METRICS.render(), media_type="text/plain; version=0.0.4")
