"""Run the embedding, retrieval, and end-to-end release evaluation suite."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

import yaml

from eval.component_retrieval import run as run_component
from eval.e2e import run as run_e2e
from eval.gate import evaluate as evaluate_gate
from eval.golden import load_golden
from eval.module_embedding import run as run_embedding
from eval.seeding import seed_all
from rag.config import ROOT, get_settings


def collect_suite(settings=None, *, write_judge_labels: bool = False) -> dict[str, Any]:
    """Collect actual module, component, and end-to-end metrics once."""
    settings = settings or get_settings(llm_api_key="")
    seed_all(settings.seed)
    embedding = run_embedding(settings=settings, write_result=False)
    component = run_component(settings=settings, top_k=settings.top_k, write_result=False)
    end_to_end = run_e2e(settings=settings, write_result=False, write_judge_labels=write_judge_labels)
    return {
        "embedding": embedding,
        "component_retrieval": component,
        "end_to_end": end_to_end,
    }


def _gate_metrics(collected: dict[str, Any]) -> dict[str, Any]:
    return {
        "embedding": collected["embedding"],
        "retrieval": collected["component_retrieval"]["metrics"]["clean"],
        "end_to_end": collected["end_to_end"]["metrics"],
    }


def _markdown(result: dict[str, Any]) -> str:
    embedding = result["runs"]["embedding"]
    retrieval = result["runs"]["component_retrieval"]
    e2e = result["runs"]["end_to_end"]["metrics"]
    lines = [
        f"# RAGOps evaluation suite — {result['timestamp']}",
        "",
        f"- Collection: `{result['collection']}`",
        f"- Seed: `{result['seed']}`",
        f"- Label: {result.get('label') or '(none)'}",
        f"- Golden questions: {result['dataset']['questions']} ({result['dataset']['answerable']} answerable, {result['dataset']['unanswerable']} unanswerable, {result['dataset']['hard']} hard)",
        "",
        "## Module and component metrics",
        "",
        "| Evaluation | Metric | Value |",
        "| --- | --- | ---: |",
        f"| Embedding | Mean paraphrase cosine | {embedding['mean_paraphrase_cosine']:.6f} |",
        f"| Embedding | Mean unrelated cosine | {embedding['mean_unrelated_cosine']:.6f} |",
        f"| Embedding | Similarity gap | {embedding['similarity_gap']:.6f} |",
        f"| Embedding | Time per chunk (ms) | {embedding['embedding_time_per_chunk_ms']:.4f} |",
    ]
    for condition, metrics in retrieval["metrics"].items():
        lines.extend([
            f"| Retrieval ({condition}) | Recall@3 | {metrics['recall_at_3']:.6f} |",
            f"| Retrieval ({condition}) | Recall@5 | {metrics['recall_at_5']:.6f} |",
            f"| Retrieval ({condition}) | MRR | {metrics['mrr']:.6f} |",
            f"| Retrieval ({condition}) | nDCG@5 | {metrics['ndcg_at_5']:.6f} |",
        ])
    lines.extend([
        "",
        "## End-to-end metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Faithfulness (LLM judge mean) | {e2e['faithfulness']:.6f} |",
        f"| Correct abstention rate | {e2e['abstention_correctness']:.6f} |",
        f"| False-abstention rate | {e2e['false_abstention_rate']:.6f} |",
        f"| Citation validity | {e2e['citation_validity']:.6f} |",
        f"| Query latency p50 (ms) | {e2e['p50_latency_ms']:.3f} |",
        f"| Query latency p95 (ms) | {e2e['p95_latency_ms']:.3f} |",
        f"| Mean judge latency (ms) | {e2e['mean_judge_latency_ms']:.3f} |",
        f"| Local LLM judge calls | {e2e['llm_judge_calls']} |",
        f"| Canonical abstentions scored as no factual claims | {e2e['vacuous_truth_abstentions']} |",
        "",
        "## Release gate",
        "",
        f"- Result: **{'PASS' if result['gate']['passed'] else 'FAIL'}**",
        "",
        "| Check | Passed |",
        "| --- | --- |",
    ])
    for key, passed in result["gate"]["checks"].items():
        lines.append(f"| {key} | {'yes' if passed else 'no'} |")
    lines.extend(["", f"Gate values: `{json.dumps(result['gate']['values'], sort_keys=True)}`", ""])
    return "\n".join(lines)


def _print_summary(result: dict[str, Any]) -> None:
    embedding = result["runs"]["embedding"]
    retrieval = result["runs"]["component_retrieval"]["metrics"]
    e2e = result["runs"]["end_to_end"]["metrics"]
    print("Evaluation | Metric | Value")
    print("--- | --- | ---:")
    print(f"Embedding | Paraphrase mean cosine | {embedding['mean_paraphrase_cosine']:.6f}")
    print(f"Embedding | Unrelated mean cosine | {embedding['mean_unrelated_cosine']:.6f}")
    print(f"Embedding | Similarity gap | {embedding['similarity_gap']:.6f}")
    for condition, values in retrieval.items():
        for key in ("recall_at_3", "recall_at_5", "mrr", "ndcg_at_5"):
            print(f"Retrieval {condition} | {key} | {values[key]:.6f}")
    for key in ("faithfulness", "abstention_correctness", "false_abstention_rate", "citation_validity", "p50_latency_ms", "p95_latency_ms", "llm_judge_calls", "vacuous_truth_abstentions"):
        print(f"End-to-end | {key} | {e2e[key]}")
    print(f"Release gate | result | {'PASS' if result['gate']['passed'] else 'FAIL'}")
    for key, passed in result["gate"]["checks"].items():
        print(f"Gate | {key} | {'PASS' if passed else 'FAIL'}")


def run(*, label: str | None = None, no_gate: bool = False) -> tuple[dict[str, Any], bool]:
    settings = get_settings(llm_api_key="")
    seed_all(settings.seed)
    questions, loader_counts = load_golden()
    if settings.top_k < 5:
        raise ValueError("TOP_K must be at least 5 for recall@5 evaluation")
    collected = collect_suite(settings, write_judge_labels=True)
    metrics = _gate_metrics(collected)
    results_dir = ROOT / "eval" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = results_dir / "baseline.json"
    baseline_created = not baseline_path.exists()
    if baseline_created:
        baseline_path.write_text(json.dumps({
            "name": "first measured suite run",
            "created_from_first_run": True,
            "metrics": metrics,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    (results_dir / "candidate.json").write_text(json.dumps({"name": label or "current run", "metrics": metrics}, indent=2, ensure_ascii=False), encoding="utf-8")
    gate_config = yaml.safe_load((ROOT / "gate.yaml").read_text(encoding="utf-8")) or {}
    gate = {"passed": True, "skipped": True, "checks": {}, "values": {}, "rationale": "Gate skipped by --no-gate."}
    if not no_gate:
        gate = evaluate_gate({"metrics": metrics}, baseline, gate_config)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result_id": f"suite_{stamp}",
        "label": label,
        "seed": settings.seed,
        "collection": settings.collection,
        "embedding_model": settings.embed_model,
        "llm_model": settings.llm_model,
        "temperature": 0,
        "baseline_created_from_this_run": baseline_created,
        "baseline_file": str(baseline_path),
        "dataset": {
            "questions": len(questions),
            "answerable": sum(row["expected_behavior"] == "answer" for row in questions),
            "unanswerable": sum(row["expected_behavior"] == "abstain" for row in questions),
            "hard": sum(row["type"] == "hard" for row in questions),
            **loader_counts,
        },
        "runs": collected,
        "metrics": metrics,
        "gate": gate,
    }
    json_path = results_dir / f"suite_{stamp}.json"
    md_path = results_dir / f"suite_{stamp}.md"
    result["result_file"] = str(json_path)
    result["summary_file"] = str(md_path)
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_markdown(result), encoding="utf-8")
    _print_summary(result)
    print(f"JSON result: {json_path}")
    print(f"Markdown summary: {md_path}")
    print(f"Baseline: {baseline_path}")
    return result, bool(gate["passed"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", help="Optional descriptive label for this run")
    parser.add_argument("--no-gate", action="store_true", help="Write all reports without applying the release gate")
    args = parser.parse_args(argv)
    try:
        _, passed = run(label=args.label, no_gate=args.no_gate)
        return 0 if passed else 1
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
