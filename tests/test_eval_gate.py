from __future__ import annotations

import pytest

from eval.gate import config_path, evaluate


@pytest.fixture
def gate_config():
    return {
        "rationale": "test thresholds",
        "thresholds": {
            "max_recall_at_5_drop": 0.02,
            "min_faithfulness": 0.95,
            "min_citation_validity": 0.90,
            "max_p95_latency_ms": 30000,
            "require_abstention_not_below_baseline": True,
        },
    }


def metrics(*, recall=0.93, faithfulness=0.98, citation=0.95, p95=25000, abstention=1.0):
    return {
        "metrics": {
            "retrieval": {"recall_at_5": recall},
            "end_to_end": {
                "faithfulness": faithfulness,
                "citation_validity": citation,
                "p95_latency_ms": p95,
                "abstention_correctness": abstention,
            },
        }
    }


def baseline():
    return metrics(recall=0.95, faithfulness=1.0, citation=1.0, p95=18547.96, abstention=1.0)


def test_candidate_inside_all_limits_passes(gate_config):
    result = evaluate(metrics(), baseline(), gate_config)
    assert result["passed"]
    assert all(result["checks"].values())
    assert result["values"]["recall_drop"] == pytest.approx(0.02)


@pytest.mark.parametrize(
    ("override", "failed_rule"),
    [
        ({"recall": 0.929}, "recall_at_5_drop_within_limit"),
        ({"faithfulness": 0.949}, "faithfulness_at_least_minimum"),
        ({"citation": 0.899}, "citation_validity_at_least_minimum"),
        ({"p95": 30000.1}, "p95_latency_within_limit"),
        ({"abstention": 0.999}, "abstention_correctness_not_below_baseline"),
    ],
)
def test_each_threshold_fails_independently(gate_config, override, failed_rule):
    result = evaluate(metrics(**override), baseline(), gate_config)
    assert not result["passed"]
    assert result["checks"][failed_rule] is False


def test_mounted_gate_config_environment_override(monkeypatch, tmp_path):
    mounted = tmp_path / "mounted-gate.yaml"
    mounted.write_text("thresholds: {}\n", encoding="utf-8")
    monkeypatch.setenv("GATE_CONFIG", str(mounted))
    assert config_path() == mounted.resolve()
    explicit = tmp_path / "explicit.yaml"
    assert config_path(str(explicit)) == explicit.resolve()
