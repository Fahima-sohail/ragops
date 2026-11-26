"""Module-level local embedding checks over curated pairs and indexed chunks."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys
from typing import Any

import numpy as np

from rag.config import ROOT, get_settings
from rag.embeddings import cosine, embed_texts, embedding_version
from rag.store import open_read_collection
from eval.seeding import seed_all


def run(settings=None, write_result: bool = True) -> dict[str, Any]:
    settings = settings or get_settings(llm_api_key="")
    seed_all(settings.seed)
    pairs_path = ROOT / "eval" / "embedding_pairs.json"
    pairs = json.loads(pairs_path.read_text(encoding="utf-8"))
    if len(pairs) < 15:
        raise ValueError("embedding evaluation requires at least 15 paraphrase and 15 unrelated pairs")
    paraphrases = [pair["paraphrase"] for pair in pairs]
    unrelated = [pair["unrelated"] for pair in pairs]
    if any(len(pair) != 2 for pair in paraphrases + unrelated):
        raise ValueError("each embedding pair must contain exactly two texts")
    all_texts = [text for pair in paraphrases + unrelated for text in pair]
    vectors, pair_elapsed = embed_texts(all_texts, settings.embed_model, settings.local_device)
    pair_scores = [cosine(vectors[index], vectors[index + 1]) for index in range(0, len(vectors), 2)]
    split = len(paraphrases)
    positive_scores, negative_scores = pair_scores[:split], pair_scores[split:]

    _, collection = open_read_collection(settings)
    active = collection.get(where={"status": "active"}, include=["documents"])
    chunks = [str(text or "") for text in active.get("documents", [])]
    if not chunks:
        raise ValueError(f"collection {settings.collection!r} has no active chunks to time")
    _, chunk_elapsed = embed_texts(chunks, settings.embed_model, settings.local_device)
    sample = "Determinism check: embed this same text twice with the cached local model."
    first, _ = embed_texts([sample], settings.embed_model, settings.local_device)
    second, _ = embed_texts([sample], settings.embed_model, settings.local_device)
    largest_difference = float(np.max(np.abs(np.asarray(first[0], dtype=np.float64) - np.asarray(second[0], dtype=np.float64))))

    result: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": settings.seed,
        "collection": settings.collection,
        "model": settings.embed_model,
        "embedding_version": embedding_version(settings.embed_model),
        "paraphrase_pairs": len(positive_scores),
        "unrelated_pairs": len(negative_scores),
        "mean_paraphrase_cosine": round(statistics.fmean(positive_scores), 6),
        "mean_unrelated_cosine": round(statistics.fmean(negative_scores), 6),
        "similarity_gap": round(statistics.fmean(positive_scores) - statistics.fmean(negative_scores), 6),
        "embedding_time_per_chunk_ms": round(chunk_elapsed / len(chunks), 6),
        "timed_active_chunks": len(chunks),
        "pair_embedding_elapsed_ms": round(pair_elapsed, 3),
        "determinism_largest_absolute_difference": largest_difference,
    }
    if write_result:
        results = ROOT / "eval" / "results"
        results.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        result["result_file"] = str(results / f"embedding_{stamp}.json")
        Path(result["result_file"]).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main() -> int:
    try:
        result = run()
        print("Embedding metric | Value")
        print("--- | ---")
        for key in (
            "collection", "seed", "paraphrase_pairs", "unrelated_pairs", "mean_paraphrase_cosine",
            "mean_unrelated_cosine", "similarity_gap", "timed_active_chunks",
            "embedding_time_per_chunk_ms", "determinism_largest_absolute_difference", "result_file",
        ):
            print(f"{key} | {result[key]}")
        return 0
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
