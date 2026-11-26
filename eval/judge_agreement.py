"""Compare manual labels with LLM judge labels after at least eight reviews."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import csv
import json
from pathlib import Path
import sys
from typing import Any

from rag.config import ROOT, get_settings

FIELDS = ["id", "question", "answer", "context_excerpt", "judge_score", "my_label"]


def _label(value: str) -> tuple[int, float | None]:
    normalized = value.strip().casefold()
    positive = {"supported", "support", "yes", "true", "correct", "1"}
    negative = {"unsupported", "not supported", "no", "false", "incorrect", "0"}
    if normalized in positive:
        return 1, 1.0 if normalized == "1" else None
    if normalized in negative:
        return 0, 0.0 if normalized == "0" else None
    try:
        score = float(normalized)
    except ValueError as exc:
        raise ValueError(f"unsupported my_label {value!r}; use supported/unsupported or a score from 0 to 1") from exc
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"my_label numeric score must be between 0 and 1: {value!r}")
    return int(score >= 0.5), score


def analyze(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"CSV columns must be exactly: {', '.join(FIELDS)}")
        rows = list(reader)
    filled = [row for row in rows if str(row.get("my_label", "")).strip()]
    if len(filled) < 8:
        raise ValueError(f"Need at least 8 non-empty my_label cells; found {len(filled)}. Fill eval/judge_labels.csv and rerun.")
    agreements: list[int] = []
    score_errors: list[float] = []
    judge_positive = manual_positive = 0
    for row in filled:
        try:
            judge_score = float(row["judge_score"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{row.get('id')}: judge_score is not numeric") from exc
        if not 0.0 <= judge_score <= 1.0:
            raise ValueError(f"{row.get('id')}: judge_score must be between 0 and 1")
        manual, numeric = _label(str(row["my_label"]))
        judged = int(judge_score >= 0.5)
        agreements.append(int(judged == manual))
        judge_positive += judged
        manual_positive += manual
        if numeric is not None:
            score_errors.append(abs(numeric - judge_score))
    n = len(agreements)
    observed = sum(agreements) / n
    p_judge = judge_positive / n
    p_manual = manual_positive / n
    expected = p_judge * p_manual + (1 - p_judge) * (1 - p_manual)
    kappa = (observed - expected) / (1 - expected) if expected < 1 else (1.0 if observed == 1 else 0.0)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": get_settings().seed,
        "csv": str(path),
        "filled_labels": n,
        "minimum_required": 8,
        "threshold_for_binary_agreement": 0.5,
        "agreement_rate": round(observed, 6),
        "cohen_kappa": round(kappa, 6),
        "numeric_label_mean_absolute_error": round(sum(score_errors) / len(score_errors), 6) if score_errors else None,
        "numeric_manual_scores": len(score_errors),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=str(ROOT / "eval" / "judge_labels.csv"))
    args = parser.parse_args(argv)
    path = Path(args.csv)
    try:
        result = analyze(path)
        results_dir = ROOT / "eval" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        result_path = results_dir / f"judge_agreement_{stamp}.json"
        result["result_file"] = str(result_path)
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
