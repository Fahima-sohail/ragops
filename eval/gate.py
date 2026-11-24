"""Compare a candidate result with a baseline and enforce gate.yaml thresholds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import yaml


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("metrics", payload)


def evaluate(candidate: dict[str, Any], baseline: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    current, prior = _metrics(candidate), _metrics(baseline)
    limits = config.get("thresholds", config)
    c_recall = float(current.get("retrieval", {}).get("recall_at_5", 0.0))
    b_recall = float(prior.get("retrieval", {}).get("recall_at_5", 0.0))
    c_faith = float(current.get("end_to_end", {}).get("faithfulness", 0.0))
    c_citation = float(current.get("end_to_end", {}).get("citation_validity", 0.0))
    c_p95 = float(current.get("end_to_end", {}).get("p95_latency_ms", float("inf")))
    c_abstain = float(current.get("end_to_end", {}).get("abstention_correctness", 0.0))
    b_abstain = float(prior.get("end_to_end", {}).get("abstention_correctness", 0.0))

    checks = {
        "recall_at_5_drop_within_limit": b_recall - c_recall <= float(limits.get("max_recall_at_5_drop", 0.02)),
        "faithfulness_at_least_minimum": c_faith >= float(limits.get("min_faithfulness", 0.5)),
        "citation_validity_at_least_minimum": c_citation >= float(limits.get("min_citation_validity", 0.9)),
        "p95_latency_within_limit": c_p95 <= float(limits.get("max_p95_latency_ms", 30000)),
        "abstention_correctness_not_below_baseline": (
            c_abstain >= b_abstain
            if bool(limits.get("require_abstention_not_below_baseline", True))
            else True
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "values": {
            "baseline_recall_at_5": b_recall,
            "candidate_recall_at_5": c_recall,
            "recall_drop": b_recall - c_recall,
            "faithfulness": c_faith,
            "citation_validity": c_citation,
            "p95_latency_ms": c_p95,
            "baseline_abstention_correctness": b_abstain,
            "candidate_abstention_correctness": c_abstain,
        },
        "rationale": config.get("rationale", ""),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply the configured baseline-to-candidate release gate.")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    try:
        candidate = _load(Path(args.candidate))
        baseline = _load(Path(args.baseline))
        config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or {}
        result = evaluate(candidate, baseline, config)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    except Exception as exc:
        print(json.dumps({"passed": False, "error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
