"""Run embedding, retrieval, noisy retrieval, and end-to-end evaluation twice."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import statistics
import sys
import time
from typing import Any

import numpy as np

from eval.gate import evaluate as apply_gate
from rag.config import ROOT, get_settings
from rag.embeddings import cosine, embed_texts
from rag.generate import ABSTENTION, _meaningful, run_query, _CACHE
from rag.retrieve import retrieve
from rag.store import collection_rows, open_read_collection
from rag.trace import append_trace

NOISE_TEXTS = [
    "A glider pilot checked the wind before crossing the valley.",
    "The recipe uses ground cumin, lemon juice, and chickpeas.",
    "A ceramic artist shaped a bowl from red clay and fired it overnight.",
]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _relevance_metrics(ranked: list[tuple[str, int, float]], expected: list[dict[str, Any]], k: int) -> tuple[float, float, float]:
    expected_set = {(str(item["doc_id"]), int(item["page"])) for item in expected}
    top = ranked[:k]
    found = {(doc_id, page) for doc_id, page, _ in top if (doc_id, page) in expected_set}
    recall = len(found) / len(expected_set) if expected_set else 0.0
    ranks = [index for index, (doc_id, page, _) in enumerate(top, 1) if (doc_id, page) in expected_set]
    reciprocal = 1.0 / min(ranks) if ranks else 0.0
    dcg = sum(1.0 / np.log2(index + 1) for index, (doc_id, page, _) in enumerate(top, 1) if (doc_id, page) in expected_set)
    ideal_count = min(k, len(expected_set))
    ideal = sum(1.0 / np.log2(index + 1) for index in range(1, ideal_count + 1))
    ndcg = dcg / ideal if ideal else 0.0
    return recall, reciprocal, ndcg


def retrieval_metrics(questions: list[dict[str, Any]], settings, top_k: int) -> dict[str, Any]:
    answerable = [item for item in questions if item["answerability"] == "answerable"]
    noise_vectors, _ = embed_texts(NOISE_TEXTS, settings.embed_model, settings.local_device)
    clean_scores = {"recall_at_3": [], "recall_at_5": [], "mrr": [], "ndcg_at_5": []}
    noisy_scores = {key: [] for key in clean_scores}
    _, collection = open_read_collection(settings)
    all_count = collection.count()
    actual_k = min(top_k, max(1, all_count))
    for item in answerable:
        passages, _, _, query_vector = retrieve(item["question"], settings, actual_k)
        ranked = [(passage.doc_id, passage.page, passage.score) for passage in passages]
        expected = item.get("relevant", [])
        for key, k in (("recall_at_3", 3), ("recall_at_5", 5), ("mrr", 5), ("ndcg_at_5", 5)):
            recall, reciprocal, ndcg = _relevance_metrics(ranked, expected, k)
            clean_scores[key].append({"recall_at_3": recall, "recall_at_5": recall, "mrr": reciprocal, "ndcg_at_5": ndcg}[key])

        noise_ranked = list(ranked)
        for index, vector in enumerate(noise_vectors):
            noise_ranked.append((f"noise-{index + 1}", 1, cosine(query_vector, vector)))
        noise_ranked.sort(key=lambda row: row[2], reverse=True)
        for key, k in (("recall_at_3", 3), ("recall_at_5", 5), ("mrr", 5), ("ndcg_at_5", 5)):
            recall, reciprocal, ndcg = _relevance_metrics(noise_ranked, expected, k)
            noisy_scores[key].append({"recall_at_3": recall, "recall_at_5": recall, "mrr": reciprocal, "ndcg_at_5": ndcg}[key])

    summarize = lambda values: round(statistics.fmean(values), 6) if values else 0.0
    clean = {key: summarize(values) for key, values in clean_scores.items()}
    noisy = {key: summarize(values) for key, values in noisy_scores.items()}
    return {
        **clean,
        "answerable_questions": len(answerable),
        "noise_test": {
            "irrelevant_documents_added": len(NOISE_TEXTS),
            "metrics": noisy,
            "change": {key: round(noisy[key] - clean[key], 6) for key in clean},
        },
    }


def embedding_metrics(settings) -> dict[str, Any]:
    pairs = json.loads((ROOT / "eval" / "embedding_pairs.json").read_text(encoding="utf-8"))
    texts: list[str] = []
    for pair in pairs:
        texts.extend(pair["paraphrase"])
        texts.extend(pair["unrelated"])
    vectors, elapsed_ms = embed_texts(texts, settings.embed_model, settings.local_device)
    cursor = 0
    paraphrase_scores: list[float] = []
    unrelated_scores: list[float] = []
    for _ in pairs:
        paraphrase_scores.append(cosine(vectors[cursor], vectors[cursor + 1]))
        unrelated_scores.append(cosine(vectors[cursor + 2], vectors[cursor + 3]))
        cursor += 4
    _, collection = open_read_collection(settings)
    docs = collection_rows(collection).get("documents", [])
    chunk_vectors, chunk_elapsed = embed_texts(docs, settings.embed_model, settings.local_device)
    first, _ = embed_texts(["The same input is embedded twice to check deterministic local inference."], settings.embed_model, settings.local_device)
    second, _ = embed_texts(["The same input is embedded twice to check deterministic local inference."], settings.embed_model, settings.local_device)
    largest_difference = float(np.max(np.abs(np.asarray(first) - np.asarray(second))))
    positive = statistics.fmean(paraphrase_scores) if paraphrase_scores else 0.0
    negative = statistics.fmean(unrelated_scores) if unrelated_scores else 0.0
    return {
        "paraphrase_pairs": len(paraphrase_scores),
        "unrelated_pairs": len(unrelated_scores),
        "mean_paraphrase_cosine": round(positive, 6),
        "mean_unrelated_cosine": round(negative, 6),
        "similarity_gap": round(positive - negative, 6),
        "embedding_time_per_chunk_ms": round(chunk_elapsed / max(1, len(chunk_vectors)), 4),
        "embedding_pairs_elapsed_ms": round(elapsed_ms, 3),
        "determinism_largest_difference": largest_difference,
        "model": settings.embed_model,
    }


def _answer_metrics(questions: list[dict[str, Any]], settings, top_k: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _CACHE.clear()
    latency: list[float] = []
    answerable_count = correct_abstentions = faithfulness_count = citation_valid = citation_total = 0
    rows: list[dict[str, Any]] = []
    for item in questions:
        result = run_query(item["question"], settings=settings, top_k=top_k)
        latency.append(float(result["latency_ms"]["total"]))
        citations = result.get("citations", [])
        retrieved_keys = {(str(row["doc_id"]), int(row["page"])) for row in result.get("retrieved", [])}
        citation_ok = bool(citations) and all((str(cit["doc_id"]), int(cit["page"])) in retrieved_keys for cit in citations)
        citation_total += bool(citations)
        citation_valid += citation_ok
        answerable = item["answerability"] == "answerable"
        if answerable:
            answerable_count += 1
            expected = {(str(ref["doc_id"]), int(ref["page"])) for ref in item.get("relevant", [])}
            relevant_retrieved = bool(expected & retrieved_keys)
            answer_without_citation = str(result.get("response", "")).split(" [", 1)[0]
            evidence_text = str(result.get("prompt", ""))
            answer_terms = _meaningful(answer_without_citation)
            evidence_terms = _meaningful(evidence_text)
            lexical_support = bool(answer_terms) and len(answer_terms & evidence_terms) / len(answer_terms) >= 0.38
            faithful = bool(result.get("answered_from_context")) and citation_ok and relevant_retrieved and lexical_support
            faithfulness_count += faithful
        else:
            correct = result.get("response") == ABSTENTION and not citations
            correct_abstentions += correct
            faithful = False
        rows.append({
            "id": item["id"],
            "question": item["question"],
            "answerability": item["answerability"],
            "response": result["response"],
            "citations": citations,
            "faithfulness_heuristic": bool(faithful),
            "citation_valid": bool(citation_ok),
            "trace_id": result["trace_id"],
            "latency_ms": result["latency_ms"],
            "review_status": item.get("review_status", "not_reviewed"),
        })

    unanswerable = sum(item["answerability"] == "unanswerable" for item in questions)
    sorted_latency = sorted(latency)
    pct = lambda fraction: sorted_latency[min(len(sorted_latency) - 1, round((len(sorted_latency) - 1) * fraction))] if sorted_latency else 0.0
    return {
        "faithfulness": faithfulness_count / answerable_count if answerable_count else 0.0,
        "faithfulness_method": "retrieved-reference, citation, and answer-presence heuristic; no LLM judge used",
        "answerable_count": answerable_count,
        "abstention_correctness": correct_abstentions / unanswerable if unanswerable else 0.0,
        "unanswerable_count": unanswerable,
        "citation_validity": citation_valid / citation_total if citation_total else 0.0,
        "citation_count": citation_total,
        "p50_latency_ms": float(pct(0.50)),
        "p95_latency_ms": float(pct(0.95)),
        "query_count": len(questions),
    }, rows


def suite_once(questions: list[dict[str, Any]], settings, top_k: int) -> dict[str, Any]:
    started = time.perf_counter()
    retrieval = retrieval_metrics(questions, settings, top_k)
    end_to_end, rows = _answer_metrics(questions, settings, top_k)
    return {
        "top_k": top_k,
        "retrieval": retrieval,
        "end_to_end": end_to_end,
        "answers": rows,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def _metric_differences(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    diff: dict[str, Any] = {}
    for section in ("retrieval", "end_to_end"):
        diff[section] = {}
        for key, value in left[section].items():
            other = right[section].get(key)
            if isinstance(value, (int, float)) and isinstance(other, (int, float)):
                diff[section][key] = round(float(other) - float(value), 6)
    return diff


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def run(candidate_top_k: int | None = None) -> tuple[dict[str, Any], bool]:
    settings = get_settings()
    random.seed(settings.seed)
    np.random.seed(settings.seed)
    questions = _read_jsonl(ROOT / "eval" / "golden.jsonl")
    if len(questions) < 25:
        raise ValueError("golden set must contain at least 25 questions")
    if sum(item["answerability"] == "answerable" for item in questions) < 15:
        raise ValueError("golden set needs at least 15 answerable questions")
    if sum(item["answerability"] == "unanswerable" for item in questions) < 5:
        raise ValueError("golden set needs at least 5 unanswerable questions")
    if sum(item.get("difficulty") == "hard" for item in questions) < 5:
        raise ValueError("golden set needs at least 5 hard questions")
    review_complete = all(
        item.get("review_status") == "approved"
        for item in questions
        if item.get("author_type") == "human" or item.get("id") in {f"q{i:02d}" for i in range(9, 17)}
    )
    baseline_k = settings.top_k
    candidate_k = candidate_top_k or baseline_k + 1
    baseline_first = suite_once(questions, settings, baseline_k)
    baseline_second = suite_once(questions, settings, baseline_k)
    candidate_first = suite_once(questions, settings, candidate_k)
    candidate_second = suite_once(questions, settings, candidate_k)

    embedding = embedding_metrics(settings)
    embedding_second = embedding_metrics(settings)
    baseline_metrics = {"retrieval": baseline_first["retrieval"], "end_to_end": baseline_first["end_to_end"], "embedding": embedding}
    candidate_metrics = {"retrieval": candidate_first["retrieval"], "end_to_end": candidate_first["end_to_end"], "embedding": embedding}
    config = __import__("yaml").safe_load((ROOT / "gate.yaml").read_text(encoding="utf-8")) or {}
    gate = apply_gate({"metrics": candidate_metrics}, {"metrics": baseline_metrics}, config)
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": settings.seed,
        "collection": settings.collection,
        "embedding_model": settings.embed_model,
        "llm_model": settings.llm_model,
        "dataset": {
            "questions": len(questions),
            "answerable": sum(item["answerability"] == "answerable" for item in questions),
            "unanswerable": sum(item["answerability"] == "unanswerable" for item in questions),
            "hard": sum(item.get("difficulty") == "hard" for item in questions),
            "pending_reviews": sum(item.get("review_status") == "pending_user_approval" for item in questions),
            "human_review_complete": review_complete,
        },
        "provisional": not review_complete,
        "runs": {
            "baseline_run_1": baseline_first,
            "baseline_run_2": baseline_second,
            "candidate_run_1": candidate_first,
            "candidate_run_2": candidate_second,
        },
        "stochasticity_difference": {
            "embedding_run_2_minus_run_1": {
                key: round(float(embedding_second[key]) - float(value), 9)
                for key, value in embedding.items()
                if isinstance(value, (int, float)) and isinstance(embedding_second.get(key), (int, float))
            },
            "baseline_run_2_minus_run_1": _metric_differences(baseline_first, baseline_second),
            "candidate_run_2_minus_run_1": _metric_differences(candidate_first, candidate_second),
        },
        "embedding": embedding,
        "embedding_run_2": embedding_second,
        "baseline": {"name": f"TOP_K={baseline_k}", "metrics": baseline_metrics},
        "candidate": {"name": f"TOP_K={candidate_k}", "metrics": candidate_metrics},
        "gate": gate,
    }
    results_dir = ROOT / "eval" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result_path = results_dir / f"suite_{stamp}.json"
    _write_json(result_path, result)
    _write_json(results_dir / "baseline.json", {"name": result["baseline"]["name"], "metrics": baseline_metrics, "run": baseline_first})
    _write_json(results_dir / "candidate.json", {"name": result["candidate"]["name"], "metrics": candidate_metrics, "run": candidate_first})

    # Leave eight actual generated responses with evidence and proposed labels for
    # the requested human judge review. They are never treated as approved here.
    review_rows = baseline_first["answers"][:8]
    review = [
        "# Faithfulness judge review draft\n\n**Status: pending user approval.** These are actual responses from the local pipeline. The proposed labels use the disclosed heuristic and need a human review before they become final. No LLM judge is used in reported metrics.\n",
        "| ID | Question | Proposed label | Retrieved citation | Pipeline answer | Review status |\n| --- | --- | --- | --- | --- | --- |",
    ]
    for row in review_rows:
        label = "supported" if row["faithfulness_heuristic"] else "unsupported or abstained"
        citation = "; ".join(f"{item['title']} v{item['doc_version']} p.{item['page']}" for item in row["citations"]) or "none"
        review.append(f"| {row['id']} | {row['question']} | {label} | {citation} | {row['response'].replace('|', '/')[:240]} | Pending |")
    (ROOT / "eval" / "review" / "judge_answers.md").write_text("\n".join(review) + "\n", encoding="utf-8")
    print(json.dumps({"result_file": str(result_path), "gate": gate, "provisional": result["provisional"], "baseline_TOP_K": baseline_k, "candidate_TOP_K": candidate_k}, indent=2))
    return result, bool(gate["passed"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-top-k", type=int)
    args = parser.parse_args(argv)
    try:
        _, passed = run(args.candidate_top_k)
        return 0 if passed else 1
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
