"""Read-only query API and trace-derived metrics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import time
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag.config import get_settings
from rag.generate import run_query
from rag.trace import summarize_traces

app = FastAPI(title="RAGOps API", version="1.0.0")
settings = get_settings()


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=30)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "collection": settings.collection, "vector_dir_exists": settings.vector_dir.exists()}


@app.post("/query")
def query(request: QueryRequest) -> dict[str, Any]:
    try:
        result = run_query(request.query, settings=settings, top_k=request.top_k)
        return {
            "trace_id": result["trace_id"],
            "answer": result["response"],
            "citations": result["citations"],
            "retrieved": result["retrieved"],
            "guardrail_actions": result["guardrail_actions"],
            "latency_ms": result["latency_ms"],
            "cache_hit": result["cache_hit"],
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"query pipeline unavailable: {type(exc).__name__}") from exc


@app.get("/metrics")
def metrics(window_hours: int = 24) -> dict[str, Any]:
    if window_hours < 1 or window_hours > 8760:
        raise HTTPException(status_code=400, detail="window_hours must be between 1 and 8760")
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    return {"window_hours": window_hours, **summarize_traces(settings.trace_dir, since)}
