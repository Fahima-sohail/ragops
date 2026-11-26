"""Run the full evaluation twice and report every numeric metric difference."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from eval.run_suite import collect_suite
from eval.seeding import seed_all
from rag.config import ROOT, get_settings
from rag.generate import _CACHE


def _snapshot(collected: dict[str, Any]) -> dict[str, Any]:
    return {
        "embedding": collected["embedding"],
        "retrieval": {
            "metrics": collected["component_retrieval"]["metrics"],
            "changes_vs_clean": collected["component_retrieval"]["changes_vs_clean"],
            "noise_documents_added": collected["component_retrieval"]["noise_test"]["noise_documents_added"],
            "main_collection_unchanged": collected["component_retrieval"]["noise_test"]["main_collection_unchanged"],
        },
        "end_to_end": collected["end_to_end"]["metrics"],
    }


def _flatten(value: Any, prefix: str = "") -> dict[str, float | str | bool | None]:
    result: dict[str, float | str | bool | None] = {}
    if isinstance(value, dict):
        for key in sorted(value):
            path = f"{prefix}.{key}" if prefix else str(key)
            result.update(_flatten(value[key], path))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        result[prefix] = float(value)
    elif isinstance(value, (str, bool)) or value is None:
        result[prefix] = value
    return result


def _explanation(metric: str) -> str:
    key = metric.casefold()
    if "latency" in key or "time_per_chunk" in key or "elapsed" in key:
        return "Host scheduling, model warm-up, and cache state can change measured runtime."
    if "faithfulness" in key or "citation_validity" in key or "abstention" in key or "judge" in key:
        return "The local language model can vary its generated answer or judge JSON despite temperature zero."
    if "recall" in key or "mrr" in key or "ndcg" in key or "similarity" in key or "cosine" in key or "gap" in key:
        return "Embedding/runtime variation or tied similarity scores can change ranking metrics."
    return "A numeric metric changed between repeated seeded runs; inspect its underlying report and runtime inputs."


def compare(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    left, right = _flatten(first), _flatten(second)
    rows = []
    for name in sorted(set(left) | set(right)):
        a, b = left.get(name), right.get(name)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            difference = round(float(b) - float(a), 9)
            rows.append({
                "metric": name,
                "run_1": a,
                "run_2": b,
                "difference_run_2_minus_run_1": difference,
                "explanation": _explanation(name) if difference != 0 else "No observed difference between the two runs.",
            })
        elif a != b:
            rows.append({
                "metric": name,
                "run_1": a,
                "run_2": b,
                "difference_run_2_minus_run_1": None,
                "explanation": "Non-numeric run metadata differs; it has no arithmetic metric difference.",
            })
    changed = [row for row in rows if row["difference_run_2_minus_run_1"] not in (0, None)]
    return {
        "metric_count": len(rows),
        "nonzero_numeric_difference_count": len(changed),
        "all_differences": rows,
        "nonzero_differences": changed,
    }


def run() -> dict[str, Any]:
    settings = get_settings(llm_api_key="")
    seed_all(settings.seed)
    _CACHE.clear()
    first = _snapshot(collect_suite(settings, write_judge_labels=False))
    seed_all(settings.seed)
    _CACHE.clear()
    second = _snapshot(collect_suite(settings, write_judge_labels=False))
    comparison = compare(first, second)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_dir = ROOT / "eval" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / f"stochasticity_{stamp}.json"
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": settings.seed,
        "collection": settings.collection,
        "embedding_model": settings.embed_model,
        "llm_model": settings.llm_model,
        "temperature": 0,
        "run_1": first,
        "run_2": second,
        "comparison": comparison,
        "result_file": str(path),
    }
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Metric | Run 1 | Run 2 | Difference | Explanation")
    print("--- | ---: | ---: | ---: | ---")
    for row in comparison["all_differences"]:
        print(f"{row['metric']} | {row['run_1']} | {row['run_2']} | {row['difference_run_2_minus_run_1']} | {row['explanation']}")
    print(json.dumps({
        "metric_count": comparison["metric_count"],
        "nonzero_numeric_difference_count": comparison["nonzero_numeric_difference_count"],
        "result_file": str(path),
    }, indent=2))
    return result


def main() -> int:
    try:
        run()
        return 0
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
