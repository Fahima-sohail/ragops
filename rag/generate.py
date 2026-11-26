"""Grounded query pipeline with citation validation, caching, and JSONL traces."""

from __future__ import annotations

import hashlib
import re
import threading
import time
import uuid
from typing import Any

from rag.config import Settings, get_settings
from rag.embeddings import embedding_version
from rag.guardrail import screen_passages, screen_query
from rag.llm import build_prompt, generate as call_llm, parse_answer
from rag.retrieve import Passage, retrieve
from rag.store import collection_generation, open_read_collection
from rag.trace import append_trace

ABSTENTION = "I don't know based on the documents"
_STOP = {
    "a", "about", "an", "and", "are", "as", "at", "be", "by", "can", "does", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "what", "when", "where", "which", "who", "with",
}
_WORD = re.compile(r"[a-z0-9]+", re.I)
_BOILERPLATE_QUERY_TERMS = {"aster", "research", "lab"}
_CACHE: dict[tuple[str, str, str, int, str, float], dict[str, Any]] = {}
_CACHE_LOCK = threading.RLock()


def _meaningful(text: str) -> set[str]:
    return {token.casefold() for token in _WORD.findall(text) if token.casefold() not in _STOP and len(token) > 2}


def _supported(answer: str, passages: list[Passage]) -> bool:
    answer_terms = _meaningful(answer)
    if not answer_terms:
        return False
    evidence_terms = set().union(*(_meaningful(passage.text) for passage in passages)) if passages else set()
    return len(answer_terms & evidence_terms) / len(answer_terms) >= 0.38


def _context_supports_question(question: str, passages: list[Passage]) -> bool:
    # Corpus-wide organization words are not evidence that a passage answers a
    # question about a specific person, room, or live fact.
    query_terms = _meaningful(question) - _BOILERPLATE_QUERY_TERMS
    if not query_terms or not passages:
        return False
    for passage in passages:
        overlap = len(query_terms & _meaningful(passage.text))
        if overlap >= min(2, len(query_terms)) and overlap / len(query_terms) >= 0.2:
            return True
    return False


def _extractive_fallback(question: str, passages: list[Passage]) -> str | None:
    query_terms = _meaningful(question)
    best: tuple[float, str] | None = None
    for passage in passages:
        for sentence in re.split(r"(?<=[.!?])\s+", " ".join(passage.text.split())):
            sentence_terms = _meaningful(sentence)
            overlap = len(query_terms & sentence_terms)
            ratio = overlap / max(1, len(query_terms))
            if overlap >= 2 and (best is None or ratio > best[0]):
                best = (ratio, sentence.strip())
    return best[1] if best else None


def _citation(passage: Passage) -> dict[str, Any]:
    result = passage.citation()
    result["inline"] = f"[{passage.title} v{passage.doc_version}, p. {passage.page}]"
    return result


def _best_citation_passage(answer: str, passages: list[Passage]) -> Passage:
    """Cite the retrieved passage with the strongest lexical support for the answer."""
    if not passages:
        raise ValueError("cannot select a citation without retrieved evidence")
    answer_terms = _meaningful(answer)
    if not answer_terms:
        return passages[0]
    return sorted(
        passages,
        key=lambda passage: (
            -len(answer_terms & _meaningful(passage.text)) / len(answer_terms),
            -passage.score,
            passage.chunk_id,
        ),
    )[0]


def _cached_result_key(query: str, settings: Settings, top_k: int) -> tuple[str, str, str, int, str, float]:
    _, collection = open_read_collection(settings)
    return (
        query.strip().casefold(),
        settings.collection,
        collection_generation(collection, settings.vector_dir),
        top_k,
        settings.embed_model,
        settings.similarity_threshold,
    )


def run_query(query: str, settings: Settings | None = None, top_k: int | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    top_k = top_k or settings.top_k
    started = time.perf_counter()
    trace_id = str(uuid.uuid4())
    safe_query, query_actions = screen_query(query)
    cache_hit = False
    key: tuple[str, str, str, int, str, float] | None = None

    if safe_query:
        key = _cached_result_key(safe_query, settings, top_k)
        with _CACHE_LOCK:
            cached = _CACHE.get(key)
        if cached is not None:
            cache_hit = True
            result = dict(cached)
            result["trace_id"] = trace_id
            result["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            result["user_query"] = query
            result["rewritten_query"] = safe_query
            result["cache_hit"] = True
            result["latency_ms"] = {"embed": 0.0, "retrieve": 0.0, "rerank": 0.0, "generate": 0.0, "total": round((time.perf_counter() - started) * 1000.0, 3)}
            append_trace(result, settings.trace_dir)
            return result

    passages: list[Passage] = []
    embed_ms = retrieve_ms = rerank_ms = generation_ms = 0.0
    if safe_query:
        passages, embed_ms, retrieve_ms, _ = retrieve(safe_query, settings, top_k)
    safe_passages, passage_actions = screen_passages(passages)
    actions = query_actions + passage_actions
    top1_similarity = passages[0].score if passages else 0.0
    evidence = safe_passages if top1_similarity >= settings.similarity_threshold and _context_supports_question(safe_query, safe_passages) else []
    prompt_items = [
        {"title": p.title, "version": p.doc_version, "page": str(p.page), "text": p.text}
        for p in evidence
    ]
    prompt_question = safe_query if safe_query else "[blocked prompt injection query]"
    prompt = build_prompt(prompt_question, prompt_items)

    if not evidence:
        answer = ABSTENTION
        citations: list[dict[str, Any]] = []
        confidence = "low"
        answered_from_context = False
    else:
        generation_started = time.perf_counter()
        raw = call_llm(prompt, settings, temperature=0.0)
        generation_ms = (time.perf_counter() - generation_started) * 1000.0
        answer, answered_from_context, confidence = parse_answer(raw)
        if not answer or not answered_from_context:
            answer = _extractive_fallback(query, evidence) or ""
            answered_from_context = bool(answer)
        if answered_from_context and not _supported(answer, evidence):
            fallback = _extractive_fallback(query, evidence)
            if fallback:
                answer = fallback
                supporting_passage = next((passage for passage in evidence if fallback in passage.text), evidence[0])
                actions.append({
                    "rule_name": "unsupported_generation",
                    "chunk_id": supporting_passage.chunk_id,
                    "doc_id": supporting_passage.doc_id,
                    "action_taken": "replaced_with_extractive_evidence",
                })
            else:
                answer = ""
                answered_from_context = False
        if not answered_from_context:
            answer = ABSTENTION
            citations = []
            confidence = "low"
        else:
            cited_passage = _best_citation_passage(answer, evidence)
            citations = [_citation(cited_passage)]
            answer = f"{answer.rstrip()} {citations[0]['inline']}"

    total_ms = (time.perf_counter() - started) * 1000.0
    trace: dict[str, Any] = {
        "trace_id": trace_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "user_query": query,
        "rewritten_query": query,
        "embedding_model": settings.embed_model,
        "embedding_version": embedding_version(settings.embed_model),
        "collection": settings.collection,
        "retrieved": [
            {
                "chunk_id": p.chunk_id,
                "doc_id": p.doc_id,
                "doc_version": p.doc_version,
                "score": round(p.score, 6),
            }
            for p in passages
        ],
        "filters": {"status": "active", "top_k": top_k, "minimum_similarity": settings.similarity_threshold},
        "reranked_order": [p.chunk_id for p in passages],
        "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt": prompt,
        "model": settings.llm_model,
        "params": {"temperature": 0, "top_k": top_k, "confidence": confidence},
        "response": answer,
        "citations": citations,
        "guardrail_actions": actions,
        "latency_ms": {
            "embed": round(embed_ms, 3),
            "retrieve": round(retrieve_ms, 3),
            "rerank": round(rerank_ms, 3),
            "generate": round(generation_ms, 3),
            "total": round(total_ms, 3),
        },
        "cache_hit": cache_hit,
    }
    append_trace(trace, settings.trace_dir)
    if key is not None:
        with _CACHE_LOCK:
            _CACHE[key] = {**trace, "cache_hit": False}
    return trace
