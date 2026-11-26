"""End-to-end golden evaluation with a deterministic LLM grounding judge."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import csv
import json
from pathlib import Path
import re
import random
import statistics
import sys
import time
from typing import Any

from eval.golden import load_golden
from eval.seeding import seed_all
from rag.config import ROOT, Settings, get_settings
from rag.generate import ABSTENTION, _CACHE, run_query
from rag.llm import generate as generate_text
from rag.store import open_read_collection

LABEL_FIELDS = ["id", "question", "answer", "context_excerpt", "judge_score", "my_label"]

JUDGE_SYSTEM_PROMPT = (
    "You are a strict evidence judge. Decide whether every factual claim in ANSWER is supported by CONTEXT. "
    "If ANSWER is exactly 'I don't know based on the documents', return score 1, reason 'Abstention makes no "
    "factual claims.', and citation_supported false. Otherwise, return exactly one JSON object: "
    "{\"score\": number from 0 to 1, \"reason\": \"one short sentence\", \"citation_supported\": boolean}. "
    "Use 1 for fully supported, 0 for unsupported, and an intermediate score for partly supported. Set "
    "citation_supported true only if the citation source and page occur in CONTEXT and support ANSWER. Never return a bare number."
)


def _prompt_context(prompt: str) -> str:
    start_marker = "UNTRUSTED RETRIEVED EVIDENCE START\n"
    end_marker = "\nUNTRUSTED RETRIEVED EVIDENCE END"
    start = prompt.find(start_marker)
    end = prompt.find(end_marker)
    if start < 0 or end < 0 or end < start:
        return ""
    return prompt[start + len(start_marker):end].strip()


def _load_retrieved_content(collection, result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    ids = [str(row["chunk_id"]) for row in result.get("retrieved", []) if row.get("chunk_id")]
    if not ids:
        return {}
    payload = collection.get(ids=ids, include=["documents", "metadatas"])
    return {
        str(chunk_id): {"text": str(text or ""), **(metadata or {})}
        for chunk_id, text, metadata in zip(payload.get("ids", []), payload.get("documents", []), payload.get("metadatas", []))
    }


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"true", "yes", "1"}


def _parse_judge(raw: str, citation_checks: list[dict[str, Any]]) -> dict[str, Any]:
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        scalar = raw.strip()
        if re.fullmatch(r"(?:0(?:\.\d+)?|1(?:\.0+)?)", scalar):
            score = float(scalar)
            citation_supported = score == 1.0 and bool(citation_checks) and all(
                item.get("retrieved_location_matches") and item.get("present_in_safe_prompt")
                for item in citation_checks
            )
            return {
                "score": score,
                "reason": (
                    "The local judge found the answer supported by the cited passage."
                    if score == 1.0 else
                    "The local judge found the answer unsupported by the cited passage."
                    if score == 0.0 else
                    "The local judge found partial support in the cited passage."
                ),
                "citation_supported": citation_supported,
                "output_format": "bare_numeric_score",
            }
        raise ValueError("judge did not return a JSON object or a bare 0/1 score")
    payload = json.loads(raw[start:end + 1])
    score = float(payload["score"])
    if not 0.0 <= score <= 1.0:
        raise ValueError("judge score must be between 0 and 1")
    reason = " ".join(str(payload.get("reason", "")).split())[:240]
    return {
        "score": score,
        "reason": reason or "No reason returned by judge.",
        "citation_supported": _as_bool(payload.get("citation_supported", False)),
        "output_format": "json",
    }


def _citation_context(citations: list[dict[str, Any]], retrieved: dict[str, dict[str, Any]], fallback: str) -> str:
    """Give the judge the cited retrieved passage(s), keeping its evidence focused."""
    passages: list[str] = []
    for citation in citations:
        chunk_id = str(citation.get("chunk_id", ""))
        row = retrieved.get(chunk_id)
        if not row:
            continue
        passages.append(
            f"[Cited Evidence; {row.get('title', '')} v{row.get('doc_version', '')}; "
            f"page {row.get('page', '')}; doc_id {row.get('doc_id', '')}]\n{row.get('text', '')}"
        )
    return "\n\n".join(passages) if passages else fallback


def _judge(question: str, answer: str, context: str, citations: list[dict[str, Any]], citation_checks: list[dict[str, Any]], settings: Settings) -> tuple[dict[str, Any], float, str | None]:
    if answer.strip() == ABSTENTION:
        return {
            "score": 1.0,
            "reason": "The canonical abstention contains no factual claims.",
            "citation_supported": False,
            "output_format": "vacuous_truth_abstention",
        }, 0.0, None
    payload = {
        "question": question,
        "answer": answer,
        "retrieved_context": context,
        "citations": citations,
        "citation_location_checks": citation_checks,
    }
    started = time.perf_counter()
    raw = generate_text(
        json.dumps(payload, ensure_ascii=False),
        settings,
        max_new_tokens=180,
        system_prompt=JUDGE_SYSTEM_PROMPT,
        temperature=0.0,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    try:
        return _parse_judge(raw, citation_checks), elapsed_ms, None
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return {
            "score": 0.0,
            "reason": f"Judge output invalid: {type(exc).__name__}.",
            "citation_supported": False,
            "output_format": "invalid",
        }, elapsed_ms, raw


def _citation_checks(citations: list[dict[str, Any]], retrieved: dict[str, dict[str, Any]], context: str) -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []
    for citation in citations:
        chunk_id = str(citation.get("chunk_id", ""))
        row = retrieved.get(chunk_id)
        page = int(citation.get("page", 0) or 0)
        doc_id = str(citation.get("doc_id", ""))
        page_matches = bool(row) and str(row.get("doc_id", "")) == doc_id and int(row.get("page", 0) or 0) == page
        version_matches = bool(row) and str(row.get("doc_version", "")) == str(citation.get("doc_version", ""))
        title = str(citation.get("title", ""))
        version = str(citation.get("doc_version", ""))
        header_present = bool(title and f"{title} v{version}; page {page}" in context)
        checks.append({
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "page": page,
            "retrieved_location_matches": page_matches and version_matches,
            "present_in_safe_prompt": header_present,
        })
    structurally_valid = all(
        item["retrieved_location_matches"] and item["present_in_safe_prompt"]
        for item in checks
    )
    return checks, structurally_valid


def _write_judge_labels(answers: list[dict[str, Any]], seed: int) -> Path:
    path = ROOT / "eval" / "judge_labels.csv"
    preserved: dict[str, dict[str, str]] = {}
    if path.is_file():
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("id"):
                    preserved[str(row["id"])] = {key: str(row.get(key, "")) for key in LABEL_FIELDS}
    rng = random.Random(seed)
    sampled = rng.sample(answers, min(10, len(answers)))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        for row in sampled:
            current = {
                "id": row["id"],
                "question": row["question"],
                "answer": row["answer"],
                "context_excerpt": row["context_excerpt"][:1200],
                "judge_score": f"{row['faithfulness_score']:.6f}",
            }
            prior = preserved.get(str(row["id"]), {})
            unchanged_sample = all(prior.get(key, "") == value for key, value in current.items())
            writer.writerow({**current, "my_label": prior.get("my_label", "") if unchanged_sample else ""})
    return path


def run(settings: Settings | None = None, write_result: bool = True, write_judge_labels: bool = True) -> dict[str, Any]:
    settings = settings or get_settings(llm_api_key="")
    if settings.llm_api_key:
        from dataclasses import replace
        settings = replace(settings, llm_api_key="")
    seed_all(settings.seed)
    questions, loader_counts = load_golden()
    _CACHE.clear()
    _, collection = open_read_collection(settings)
    answers: list[dict[str, Any]] = []
    latencies: list[float] = []
    judge_latencies: list[float] = []
    correct_abstentions = false_abstentions = 0
    unanswerable_count = sum(row["expected_behavior"] == "abstain" for row in questions)
    answer_expected_count = sum(row["expected_behavior"] == "answer" for row in questions)
    citation_evaluable = citation_valid_count = 0

    for item in questions:
        result = run_query(item["question"], settings=settings, top_k=settings.top_k)
        answer = str(result.get("response", ""))
        citations = list(result.get("citations", []))
        context = _prompt_context(str(result.get("prompt", "")))
        retrieved_content = _load_retrieved_content(collection, result)
        citation_checks, structural_citation_valid = _citation_checks(citations, retrieved_content, context)
        judged_context = _citation_context(citations, retrieved_content, context)
        judged, judge_ms, invalid_raw = _judge(
            str(item["question"]), answer, judged_context, citations, citation_checks, settings
        )
        expected_behavior = item["expected_behavior"]
        is_abstention = answer == ABSTENTION
        abstention_correct = expected_behavior == "abstain" and is_abstention and not citations
        if expected_behavior == "abstain":
            correct_abstentions += int(abstention_correct)
        if expected_behavior == "answer":
            false_abstentions += int(is_abstention)
        if expected_behavior == "answer" or citations or not is_abstention:
            citation_evaluable += 1
            citation_ok = bool(citations) and structural_citation_valid and judged["citation_supported"] and not is_abstention
            citation_valid_count += int(citation_ok)
        else:
            citation_ok = not citations
        latency = float(result.get("latency_ms", {}).get("total", 0.0))
        latencies.append(latency)
        if judge_ms > 0:
            judge_latencies.append(judge_ms)
        row = {
            "id": item["id"],
            "question": item["question"],
            "type": item["type"],
            "source": item["source"],
            "reviewed": item["reviewed"],
            "expected_behavior": expected_behavior,
            "answer": answer,
            "citations": citations,
            "retrieved": result.get("retrieved", []),
            "citation_location_checks": citation_checks,
            "citation_valid": bool(citation_ok),
            "faithfulness_score": round(float(judged["score"]), 6),
            "faithfulness_reason": judged["reason"],
            "faithfulness_method": judged["output_format"],
            "citation_supported_by_judge": bool(judged["citation_supported"]),
            "abstention_correct": bool(abstention_correct),
            "false_abstention": bool(expected_behavior == "answer" and is_abstention),
            "latency_ms": latency,
            "judge_latency_ms": round(judge_ms, 3),
            "trace_id": result["trace_id"],
            "context_excerpt": context,
        }
        if invalid_raw is not None:
            row["invalid_judge_output"] = invalid_raw
        answers.append(row)

    sorted_latency = sorted(latencies)
    p50 = statistics.median(sorted_latency) if sorted_latency else 0.0
    p95 = sorted_latency[max(0, min(len(sorted_latency) - 1, int((0.95 * len(sorted_latency) + 0.999999)) - 1))] if sorted_latency else 0.0
    metrics = {
        "faithfulness": round(statistics.fmean(row["faithfulness_score"] for row in answers), 6) if answers else 0.0,
        "faithfulness_scored_questions": len(answers),
        "faithfulness_answered_only": round(statistics.fmean(row["faithfulness_score"] for row in answers if row["answer"] != ABSTENTION), 6) if any(row["answer"] != ABSTENTION for row in answers) else 0.0,
        "abstention_correctness": round(correct_abstentions / unanswerable_count, 6) if unanswerable_count else 1.0,
        "correct_abstentions": correct_abstentions,
        "unanswerable_count": unanswerable_count,
        "false_abstention_rate": round(false_abstentions / answer_expected_count, 6) if answer_expected_count else 0.0,
        "false_abstentions": false_abstentions,
        "answer_expected_count": answer_expected_count,
        "citation_validity": round(citation_valid_count / citation_evaluable, 6) if citation_evaluable else 1.0,
        "citation_valid_count": citation_valid_count,
        "citation_evaluable_count": citation_evaluable,
        "p50_latency_ms": round(float(p50), 3),
        "p95_latency_ms": round(float(p95), 3),
        "mean_judge_latency_ms": round(statistics.fmean(judge_latencies), 3) if judge_latencies else 0.0,
        "llm_judge_calls": sum(row["faithfulness_method"] != "vacuous_truth_abstention" for row in answers),
        "vacuous_truth_abstentions": sum(row["faithfulness_method"] == "vacuous_truth_abstention" for row in answers),
        "query_count": len(questions),
    }
    result: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": settings.seed,
        "collection": settings.collection,
        "embedding_model": settings.embed_model,
        "generation_and_judge_model": settings.llm_model,
        "temperature": 0,
        "golden_counts": loader_counts,
        "metrics": metrics,
        "answers": answers,
    }
    if write_judge_labels:
        result["judge_labels_csv"] = str(_write_judge_labels(answers, settings.seed))
    if write_result:
        results_dir = ROOT / "eval" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        result_path = results_dir / f"e2e_{stamp}.json"
        result["result_file"] = str(result_path)
        result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-label-sample", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run(write_result=True, write_judge_labels=not args.no_label_sample)
        print("E2E metric | Value")
        print("--- | ---")
        for key, value in result["metrics"].items():
            print(f"{key} | {value}")
        print(f"result_file | {result['result_file']}")
        if "judge_labels_csv" in result:
            print(f"judge_labels_csv | {result['judge_labels_csv']}")
        return 0
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
