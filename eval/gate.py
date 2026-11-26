"""Compare a candidate result with a baseline and enforce gate.yaml thresholds."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

import yaml

from rag.config import ROOT


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
        "recall_at_5_drop_within_limit": b_recall - c_recall <= float(limits.get("max_recall_at_5_drop", 0.02)) + 1e-9,
        "faithfulness_at_least_minimum": c_faith >= float(limits.get("min_faithfulness", 0.5)),
        "citation_validity_at_least_minimum": c_citation >= float(limits.get("min_citation_validity", 0.9)),
        "p95_latency_within_limit": c_p95 <= float(limits.get("max_p95_latency_ms", 30000)),
        "abstention_correctness_not_below_baseline": (
            c_abstain >= b_abstain
            if bool(limits.get("require_abstention_not_below_baseline", True))
            else True
        ),
    }
    thresholds = {
        "recall_at_5_drop_within_limit": f"max drop {float(limits.get('max_recall_at_5_drop', 0.02)):.4f}",
        "faithfulness_at_least_minimum": f"minimum {float(limits.get('min_faithfulness', 0.5)):.4f}",
        "citation_validity_at_least_minimum": f"minimum {float(limits.get('min_citation_validity', 0.9)):.4f}",
        "p95_latency_within_limit": f"maximum {float(limits.get('max_p95_latency_ms', 30000)):.1f} ms",
        "abstention_correctness_not_below_baseline": f"baseline {b_abstain:.4f}",
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "thresholds": thresholds,
        "values": {
            "baseline_recall_at_5": b_recall,
            "candidate_recall_at_5": c_recall,
            "recall_drop": b_recall - c_recall,
            "faithfulness": c_faith,
            "minimum_faithfulness": float(limits.get("min_faithfulness", 0.5)),
            "citation_validity": c_citation,
            "minimum_citation_validity": float(limits.get("min_citation_validity", 0.9)),
            "p95_latency_ms": c_p95,
            "maximum_p95_latency_ms": float(limits.get("max_p95_latency_ms", 30000)),
            "baseline_abstention_correctness": b_abstain,
            "candidate_abstention_correctness": c_abstain,
        },
        "rationale": config.get("rationale", ""),
    }


def config_path(cli_path: str | None = None) -> Path:
    """Resolve an explicit CLI path, mounted GATE_CONFIG, or repository default."""
    return Path(cli_path or os.environ.get("GATE_CONFIG", str(ROOT / "gate.yaml"))).expanduser().resolve()


def print_table(result: dict[str, Any]) -> None:
    print("Rule | Value / threshold | Result")
    print("--- | --- | ---")
    values = result["values"]
    thresholds = result["thresholds"]
    rows = {
        "recall_at_5_drop_within_limit": f"drop={values['recall_drop']:.4f}; {thresholds['recall_at_5_drop_within_limit']}",
        "faithfulness_at_least_minimum": f"{values['faithfulness']:.4f}; {thresholds['faithfulness_at_least_minimum']}",
        "citation_validity_at_least_minimum": f"{values['citation_validity']:.4f}; {thresholds['citation_validity_at_least_minimum']}",
        "p95_latency_within_limit": f"{values['p95_latency_ms']:.1f} ms; {thresholds['p95_latency_within_limit']}",
        "abstention_correctness_not_below_baseline": f"candidate={values['candidate_abstention_correctness']:.4f}; {thresholds['abstention_correctness_not_below_baseline']}",
    }
    for rule, passed in result["checks"].items():
        print(f"{rule} | {rows[rule]} | {'PASS' if passed else 'FAIL'}")
    print(f"Overall |  | {'PASS' if result['passed'] else 'FAIL'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply the configured baseline-to-candidate release gate.")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--config", help="Threshold file; defaults to GATE_CONFIG or gate.yaml")
    args = parser.parse_args(argv)
    try:
        candidate = _load(Path(args.candidate))
        baseline = _load(Path(args.baseline))
        selected_config = config_path(args.config)
        config = yaml.safe_load(selected_config.read_text(encoding="utf-8")) or {}
        result = evaluate(candidate, baseline, config)
        print(f"Config: {selected_config}")
        print_table(result)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    except Exception as exc:
        print(json.dumps({"passed": False, "error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
