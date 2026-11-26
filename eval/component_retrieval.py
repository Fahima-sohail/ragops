"""Component-level page retrieval metrics with isolated noise and typo runs."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import re
import statistics
import sys
from typing import Any

import chromadb
import numpy as np
from chromadb.config import Settings as ChromaSettings

from eval.golden import ground_truth_refs, load_golden, verify_ground_truth, active_page_texts
from rag.config import ROOT, get_settings
from rag.embeddings import embed_texts
from rag.retrieve import retrieve
from rag.store import collection_rows, open_read_collection
from eval.seeding import seed_all

NOISE_DOCUMENTS = [
    {
        "doc_id": "eval-noise-botany",
        "title": "Botany Field Note",
        "text": "The alpine buttercup blooms after snowmelt. Botanists record petal color and soil moisture during the summer survey.",
    },
    {
        "doc_id": "eval-noise-astronomy",
        "title": "Astronomy Club Notice",
        "text": "The meteor shower is best viewed from a dark hillside after midnight. Bring a reclining chair and a red flashlight.",
    },
    {
        "doc_id": "eval-noise-cooking",
        "title": "Kitchen Recipe Card",
        "text": "Mix chickpeas with lemon juice, olive oil, cumin, and chopped parsley. Chill the salad before serving it with flatbread.",
    },
]
_WORD = re.compile(r"[A-Za-z]{6,}")


def _unique_pairs(pairs: list[tuple[str, int]]) -> list[tuple[str, int]]:
    ranked: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            ranked.append(pair)
    return ranked


def _page_level_rank(passages) -> list[tuple[str, int]]:
    return _unique_pairs([(str(passage.doc_id), int(passage.page)) for passage in passages])


def _metrics_for_query(ranked: list[tuple[str, int]], expected: set[tuple[str, int]]) -> dict[str, float]:
    top3, top5 = ranked[:3], ranked[:5]
    reciprocal = next((1.0 / rank for rank, pair in enumerate(top5, 1) if pair in expected), 0.0)
    dcg = sum(1.0 / np.log2(rank + 1) for rank, pair in enumerate(top5, 1) if pair in expected)
    ideal_n = min(5, len(expected))
    ideal = sum(1.0 / np.log2(rank + 1) for rank in range(1, ideal_n + 1))
    return {
        "recall_at_3": len(set(top3) & expected) / len(expected),
        "recall_at_5": len(set(top5) & expected) / len(expected),
        "mrr": reciprocal,
        "ndcg_at_5": dcg / ideal if ideal else 0.0,
    }


def _summarize(values: list[dict[str, float]]) -> dict[str, float]:
    keys = ("recall_at_3", "recall_at_5", "mrr", "ndcg_at_5")
    return {key: round(statistics.fmean(row[key] for row in values), 6) if values else 0.0 for key in keys}


def _typo(question: str, rng: random.Random) -> tuple[str, str]:
    matches = list(_WORD.finditer(question))
    if not matches:
        return question, question
    match = rng.choice(matches)
    word = match.group(0)
    swap_index = rng.randrange(1, len(word) - 1)
    chars = list(word)
    chars[swap_index - 1], chars[swap_index] = chars[swap_index], chars[swap_index - 1]
    changed = "".join(chars)
    variant = question[:match.start()] + changed + question[match.end():]
    return variant, f"{word}->{changed}"


def _run_questions(questions: list[dict[str, Any]], settings, seed: int, make_typos: bool = False, collection=None) -> tuple[dict[str, float], list[dict[str, Any]]]:
    rng = random.Random(seed)
    order = list(questions)
    rng.shuffle(order)
    per_question: list[dict[str, Any]] = []
    if collection is None:
        _, read_collection = open_read_collection(settings)
        ranking_limit = read_collection.count()
    else:
        ranking_limit = collection.count()
    for item in order:
        question = str(item["question"])
        typo = None
        if make_typos:
            question, typo = _typo(question, rng)
        if collection is None:
            passages, _embed_ms, _retrieve_ms, _query_vector = retrieve(question, settings, top_k=ranking_limit)
            ranked = _page_level_rank(passages)
        else:
            vectors, _embed_ms = embed_texts([question], settings.embed_model, settings.local_device)
            raw = collection.query(
                query_embeddings=[vectors[0]],
                n_results=ranking_limit,
                where={"status": "active"},
                include=["metadatas", "distances"],
            )
            metadata = raw.get("metadatas", [[]])[0]
            distances = raw.get("distances", [[]])[0]
            ids = raw.get("ids", [[]])[0]
            ordered = sorted(
                zip(ids, metadata, distances),
                key=lambda row: (float(row[2]), str(row[0])),
            )
            ranked = _unique_pairs([
                (str(row.get("doc_id", "")), int(row.get("page", 1)))
                for _chunk_id, row, _distance in ordered if row
            ])
        expected = set(ground_truth_refs(item))
        values = _metrics_for_query(ranked, expected)
        per_question.append({"id": item["id"], "question": question, "typo": typo, **values})
    return _summarize(per_question), per_question


def _temporary_noise_collection(settings, seed: int) -> tuple[Any, Any, int]:
    _, source = open_read_collection(settings)
    source_rows = collection_rows(source)
    collection_name = f"noise_eval_{seed}"
    client = chromadb.EphemeralClient(settings=ChromaSettings(anonymized_telemetry=False))
    destination = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine", "owner": "eval.component_retrieval"},
    )
    if source_rows["ids"]:
        destination.upsert(
            ids=source_rows["ids"],
            documents=source_rows["documents"],
            metadatas=source_rows["metadatas"],
            embeddings=source_rows["embeddings"],
        )
    noise_texts = [item["text"] for item in NOISE_DOCUMENTS]
    vectors, _elapsed = embed_texts(noise_texts, settings.embed_model, settings.local_device)
    metadatas = [
        {
            "doc_id": item["doc_id"],
            "doc_version": "1.0",
            "title": item["title"],
            "source": "temporary retrieval noise fixture",
            "page": 1,
            "status": "active",
            "doc_sha256": "evaluation-only",
        }
        for item in NOISE_DOCUMENTS
    ]
    destination.upsert(
        ids=[f"{item['doc_id']}-1.0-0001" for item in NOISE_DOCUMENTS],
        documents=noise_texts,
        metadatas=metadatas,
        embeddings=vectors,
    )
    if destination.count() != source.count() + len(NOISE_DOCUMENTS):
        raise RuntimeError("temporary collection does not contain source chunks plus all noise documents")
    return client, destination, destination.count()


def run(settings=None, top_k: int | None = None, write_result: bool = True) -> dict[str, Any]:
    settings = settings or get_settings(llm_api_key="")
    if top_k is not None:
        settings = replace(settings, top_k=top_k)
    seed_all(settings.seed)
    questions, loader_counts = load_golden()
    answerable = [row for row in questions if row["expected_behavior"] == "answer"]
    if not answerable:
        raise ValueError("component retrieval requires answerable golden questions")
    pages = active_page_texts(settings)
    allow_missing = os.environ.get("EVAL_ALLOW_MISSING_GROUND_TRUTH", "0").strip().lower() in {"1", "true", "yes"}
    allow_drift = os.environ.get("EVAL_ALLOW_GROUND_TRUTH_DRIFT", "0").strip().lower() in {"1", "true", "yes"}
    verification = verify_ground_truth(
        answerable,
        pages,
        allow_missing_pages=allow_missing,
        allow_mismatched_answers=allow_drift,
    )
    _, main_collection = open_read_collection(settings)
    main_count_before = main_collection.count()

    clean, clean_rows = _run_questions(answerable, settings, settings.seed)
    typo, typo_rows = _run_questions(answerable, settings, settings.seed, make_typos=True)
    noise_client, noise_collection, noise_count = _temporary_noise_collection(settings, settings.seed)
    try:
        noisy, noisy_rows = _run_questions(answerable, settings, settings.seed, collection=noise_collection)
    finally:
        noise_collection = None
        noise_client.close()
    main_count_after = main_collection.count()
    if main_count_after != main_count_before:
        raise RuntimeError("noise evaluation changed the main collection")
    metrics = {"clean": clean, "noise_documents": noisy, "typo_queries": typo}
    result: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": settings.seed,
        "collection": settings.collection,
        "top_k": settings.top_k,
        "golden_counts": loader_counts,
        "answerable_questions": len(answerable),
        "metric_level": "unique (doc_id, page) pairs; expected pages from golden set",
        "metrics": metrics,
        "changes_vs_clean": {
            condition: {key: round(values[key] - clean[key], 6) for key in clean}
            for condition, values in (("noise_documents", noisy), ("typo_queries", typo))
        },
        "noise_test": {
            "noise_documents_added": len(NOISE_DOCUMENTS),
            "noise_doc_ids": [item["doc_id"] for item in NOISE_DOCUMENTS],
            "temporary_collection": f"noise_eval_{settings.seed}",
            "temporary_collection_kind": "ephemeral Chroma collection",
            "temporary_collection_chunk_count_before_cleanup": noise_count,
            "main_collection_count_before": main_count_before,
            "main_collection_count_after": main_count_after,
            "main_collection_unchanged": main_count_before == main_count_after,
        },
        "typo_test": {"method": "seeded adjacent-character transposition in one word per query", "seed": settings.seed},
        "ground_truth_validation": {"verified_rows": len(verification), "checks": verification},
        "allows_absent_ground_truth_pages": allow_missing,
        "allows_active_version_reference_drift": allow_drift,
        "per_question": {"clean": clean_rows, "noise_documents": noisy_rows, "typo_queries": typo_rows},
    }
    if write_result:
        results = ROOT / "eval" / "results"
        results.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        result_path = results / f"retrieval_component_{stamp}.json"
        result["result_file"] = str(result_path)
        result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-k", type=int)
    args = parser.parse_args(argv)
    try:
        settings = get_settings(llm_api_key="")
        if args.top_k is not None:
            settings = replace(settings, top_k=args.top_k)
        if settings.top_k < 5:
            raise ValueError("--top-k must be at least 5 to report recall@5")
        result = run(settings=settings, top_k=settings.top_k)
        print("Condition | Recall@3 | Recall@5 | MRR | nDCG@5")
        print("--- | ---: | ---: | ---: | ---:")
        for condition, values in result["metrics"].items():
            print(f"{condition} | {values['recall_at_3']:.6f} | {values['recall_at_5']:.6f} | {values['mrr']:.6f} | {values['ndcg_at_5']:.6f}")
        print("Change vs clean | Recall@3 | Recall@5 | MRR | nDCG@5")
        print("--- | ---: | ---: | ---: | ---:")
        for condition, values in result["changes_vs_clean"].items():
            print(f"{condition} | {values['recall_at_3']:+.6f} | {values['recall_at_5']:+.6f} | {values['mrr']:+.6f} | {values['ndcg_at_5']:+.6f}")
        print(json.dumps({"seed": result["seed"], "answerable_questions": result["answerable_questions"], "noise_documents": result["noise_test"]["noise_documents_added"], "main_collection_unchanged": result["noise_test"]["main_collection_unchanged"], "result_file": result["result_file"]}, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
