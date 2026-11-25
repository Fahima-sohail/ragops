"""Validate golden labels against the active indexed collection and save evidence."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import random
import sys
from collections import Counter
from typing import Any

import numpy as np

from eval.golden import active_page_texts, load_golden, verify_ground_truth
from rag.config import ROOT, get_settings


def run() -> dict[str, Any]:
    settings = get_settings()
    random.seed(settings.seed)
    np.random.seed(settings.seed)
    questions, loader = load_golden()
    counts = Counter(row["type"] for row in questions)
    behaviors = Counter(row["expected_behavior"] for row in questions)
    synthetic_reviewed = sum(row["source"] == "synthetic" and row["reviewed"] for row in questions)
    if len(questions) < 28 or counts["answerable"] < 18 or counts["unanswerable"] < 6 or counts["hard"] < 6:
        raise ValueError("golden minimums failed: require 28 questions, 18 answerable, 6 unanswerable, and 6 hard")
    if synthetic_reviewed != 10:
        raise ValueError(f"expected exactly 10 reviewed synthetic questions, got {synthetic_reviewed}")
    checks = verify_ground_truth(questions, active_page_texts(settings))
    result: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": settings.seed,
        "collection": settings.collection,
        "dataset": {
            "questions": len(questions),
            "answerable": counts["answerable"],
            "unanswerable": counts["unanswerable"],
            "hard": counts["hard"],
            "expected_answer": behaviors["answer"],
            "expected_abstain": behaviors["abstain"],
            "source_counts": dict(Counter(row["source"] for row in questions)),
            "reviewed_synthetic": synthetic_reviewed,
            **loader,
        },
        "ground_truth_page_checks": len(checks),
        "checks": checks,
        "all_checks_passed": True,
    }
    results = ROOT / "eval" / "results"
    results.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = results / f"golden_validation_{stamp}.json"
    result["result_file"] = str(path)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main() -> int:
    try:
        result = run()
        print("Golden validation | Value")
        print("--- | ---")
        for key, value in result["dataset"].items():
            print(f"{key} | {value}")
        print(f"ground_truth_page_checks | {result['ground_truth_page_checks']}")
        print(f"all_checks_passed | {result['all_checks_passed']}")
        print(f"result_file | {result['result_file']}")
        return 0
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
