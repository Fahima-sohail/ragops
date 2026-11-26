"""Audit the committed Member 1 evidence for Assignment 03 Parts A-E.

Run from the repository root with ``python scripts/audit.py``. Member 2-owned
live-query, coverage, trace-inspection, and Kubernetes work is reported as M2
rather than represented as completed or counted as a Member 1 failure.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "eval" / "results"
checks: list[tuple[str, str, str]] = []


def record(status: str, name: str, detail: str) -> None:
    checks.append((status, name, detail))


def check(name: str, condition: bool, detail: str) -> None:
    record("PASS" if condition else "FAIL", name, detail)


def m2(name: str, detail: str) -> None:
    record("M2", name, detail)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def result(name: str) -> Path:
    return RESULTS / name


def file_exists(name: str) -> bool:
    return (ROOT / name).is_file()


def suite(name: str) -> dict[str, Any]:
    return read_json(result(name))


def tracked_files() -> set[str]:
    try:
        data = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=ROOT, stderr=subprocess.DEVNULL
        )
        return {p.decode("utf-8") for p in data.split(b"\0") if p}
    except (OSError, subprocess.CalledProcessError):
        return set()


def trace_records(relative: str) -> list[dict[str, Any]]:
    path = ROOT / relative
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def main() -> int:
    tracked = tracked_files()

    # Part A: ingestion, verification, quarantine, incremental updates.
    batch_a = list((ROOT / "data" / "batch_a").glob("*.md"))
    batch_b = [
        p for p in (ROOT / "data" / "batch_b").iterdir()
        if p.is_file() and p.name.lower() != "planted.md"
    ]
    check("A / Batch A corpus", len(batch_a) >= 10, f"source documents={len(batch_a)} (minimum 10)")
    check("A / Batch B corpus", len(batch_b) >= 10, f"source fixtures={len(batch_b)} (minimum 10)")
    planted_path = ROOT / "data" / "batch_b" / "PLANTED.md"
    planted = planted_path.read_text(encoding="utf-8") if planted_path.exists() else ""
    planted_requirements = {
        "two exact duplicates": planted.count("Exact duplicate") >= 2,
        "near duplicate": "Near duplicate" in planted,
        "corrupt or truncated": "Corrupt extraction" in planted or "Truncated source" in planted,
        "missing metadata": "Missing metadata" in planted,
        "new version": "Newer version" in planted,
        "injection": "Prompt injection" in planted,
    }
    check("A / planted-problem manifest", all(planted_requirements.values()), ", ".join(f"{k}={'yes' if v else 'no'}" for k, v in planted_requirements.items()))

    batch_b_report_path = result("verification_20261126T102215Z-326500.json")
    batch_b_report: dict[str, Any] = {}
    try:
        batch_b_report = read_json(batch_b_report_path)
        records = {Path(x.get("path", "")).name: x for x in batch_b_report["verification"]}
        planted_checks = {
            "duplicate-intake.md": ("uniqueness", False),
            "duplicate-charter.md": ("uniqueness", False),
            "near-duplicate-intake.md": ("uniqueness", False),
            "corrupt-extraction.txt": ("quality", False),
            "truncated-fragment.md": ("completeness", False),
            "missing-metadata.md": ("completeness", False),
        }
        verification_ok = all(
            name in records
            and records[name]["checks"].get(rule) is expected
            and records[name].get("passed") is False
            for name, (rule, expected) in planted_checks.items()
        )
        check("A1 / four checks quarantine planted failures", verification_ok, "quality, completeness, recency, uniqueness are recorded per document")
        versioning = records.get("versioning-standard-v1.3.md", {})
        verification = records.get("verification-standard-v2.2.md", {})
        archived = {(x.get("doc_id"), x.get("version")) for x in batch_b_report["counts"].get("archived_versions", [])}
        version_ok = (
            versioning.get("passed") is True
            and verification.get("passed") is True
            and ("versioning-standard", "1.2") in archived
            and ("verification-standard", "2.1") in archived
        )
        check("A1 / newer versions archived", version_ok, "Batch B v1.3 and v2.2 supersede and archive the previous versions")
        injection = records.get("injection-test-record-v1.0.md", {})
        injection_intentionally_passes = injection.get("passed") is True and all(injection.get("checks", {}).values())
        check("A1 / injection fixture outcome recorded", injection_intentionally_passes, "injection is accepted by ingestion and handled by the query-time rail in Part D")
        counts = batch_b_report["counts"]
        check("A1 / per-run report and quarantine counts", counts.get("discovered_docs") == 14 and counts.get("quarantined_docs") == 6 and counts.get("embedded_chunks") == 24, f"discovered={counts.get('discovered_docs')}, quarantined={counts.get('quarantined_docs')}, embedded={counts.get('embedded_chunks')}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        check("A1 / Batch B verification evidence", False, f"cannot validate report: {exc}")

    try:
        unchanged = read_json(result("verification_20261124T194825Z-572500.json"))["counts"]
        check("A2 / unchanged rerun embeds zero", unchanged.get("embedded_chunks") == 0, f"embedded={unchanged.get('embedded_chunks')}, unchanged={unchanged.get('skipped_unchanged_chunks')}")
        changed = read_json(result("verification_20261124T195101Z-299500.json"))["counts"]
        changed_docs = changed.get("by_doc_id", {})
        check("A2 / changed document scoped replacement", changed.get("embedded_chunks") == 3 and changed_docs.get("service-charter", {}).get("replaced_chunks") == 3 and changed_docs.get("storage-backup", {}).get("skipped_unchanged_chunks") == 3, "service-charter replaced; storage-backup unchanged")
        deleted = read_json(result("verification_20261124T195240Z-941100.json"))["counts"]
        demo_log = result("A_demo_log.txt").read_text(encoding="utf-8")
        zero_orphan_proof = "source-provenance: 0" in demo_log
        deletion_test = (ROOT / "tests" / "test_ragops.py").read_text(encoding="utf-8")
        has_deletion_test = "test_sync_deletion_has_zero_chunks_and_cli_reports_zero" in deletion_test and "count_by_doc(collection, \"beta-doc\"), 0" in deletion_test
        check("A2 / deletion leaves zero orphan chunks", deleted.get("by_doc_id", {}).get("storage-backup", {}).get("deleted_chunks") == 3 and zero_orphan_proof and has_deletion_test, f"deleted chunks=3; post-delete zero printed={zero_orphan_proof}; regression test proves count zero={has_deletion_test}")
        restored = read_json(result("verification_20261124T195336Z-403600.json"))
        check("A2 / archived version restore", restored.get("restored") is True and restored.get("reactivated_chunks") == 3 and restored.get("embedded_chunks") == 0, f"restored={restored.get('restored')}, reactivated={restored.get('reactivated_chunks')}, embedded={restored.get('embedded_chunks')}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        check("A2 / manifest update evidence", False, f"cannot validate A2 reports: {exc}")
    check("A / combined demo console output", file_exists("eval/results/A_demo_log.txt"), "eval/results/A_demo_log.txt")

    # Part B: golden set, module/component/e2e evaluation, agreement, determinism.
    golden_path = ROOT / "eval" / "golden.jsonl"
    try:
        golden = [json.loads(line) for line in golden_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        counts = {key: sum(row.get("type") == key for row in golden) for key in ("answerable", "unanswerable", "hard")}
        sources = {key: sum(row.get("source") == key for row in golden) for key in ("human", "synthetic")}
        reviewed_synthetic = sum(row.get("source") == "synthetic" and row.get("reviewed") is True for row in golden)
        reviewed_human = sum(row.get("source") == "human" and row.get("reviewed") is True for row in golden)
        schema = all(all(k in row for k in ("id", "question", "type", "source", "reviewed", "ground_truth_doc", "ground_truth_page", "expected_behavior", "reference_answer")) for row in golden)
        gold_ok = len(golden) >= 25 and counts["answerable"] >= 15 and counts["unanswerable"] >= 5 and counts["hard"] >= 5 and sources["human"] >= 8 and sources["synthetic"] >= 8 and reviewed_synthetic >= 8 and schema
        check("B / golden set counts and schema", gold_ok, f"n={len(golden)} types={counts}; sources={sources}; reviewed synthetic={reviewed_synthetic}; reviewed human={reviewed_human}")
        check("B / human review and synthetic review labels", reviewed_human >= 8 and reviewed_synthetic == 10, f"reviewed human={reviewed_human} (min 8), reviewed synthetic={reviewed_synthetic} (expected 10)")
    except (OSError, ValueError, TypeError) as exc:
        check("B / golden set validation", False, f"cannot parse golden set: {exc}")

    try:
        pairs = read_json(ROOT / "eval" / "embedding_pairs.json")
        pairs_ok = isinstance(pairs, list) and len(pairs) >= 15 and all(
            isinstance(pair.get("paraphrase"), list) and len(pair["paraphrase"]) == 2
            and isinstance(pair.get("unrelated"), list) and len(pair["unrelated"]) == 2
            for pair in pairs
        )
        check("B / embedding pair set", pairs_ok, f"pairs={len(pairs) if isinstance(pairs, list) else 0}; each row must contain one paraphrase and one unrelated pair")
    except (OSError, ValueError, TypeError) as exc:
        check("B / embedding pair set", False, f"cannot parse pairs: {exc}")

    baseline_suite = {}
    candidate_suite = {}
    try:
        baseline_suite = suite("suite_20261126T155753Z.json")
        candidate_suite = suite("suite_20261126T161600Z.json")
        runs = baseline_suite.get("runs", {})
        emb = runs.get("embedding", {})
        comp = runs.get("component_retrieval", {})
        e2e = runs.get("end_to_end", {}).get("metrics", {})
        noise = comp.get("noise_test", {})
        check("B / embedding module result", emb.get("paraphrase_pairs", 0) >= 15 and emb.get("unrelated_pairs", 0) >= 15 and "similarity_gap" in emb and "determinism_largest_absolute_difference" in emb, f"paraphrase={emb.get('paraphrase_pairs')}, unrelated={emb.get('unrelated_pairs')}, gap={emb.get('similarity_gap')}")
        check("B / component clean, noise, typo metrics", all(k in comp.get("metrics", {}) for k in ("clean", "noise_documents", "typo_queries")) and noise.get("noise_documents_added", 0) >= 3 and noise.get("main_collection_unchanged") is True, f"noise docs={noise.get('noise_documents_added')}, main collection unchanged={noise.get('main_collection_unchanged')}")
        check("B / end-to-end metrics", all(k in e2e for k in ("faithfulness", "abstention_correctness", "false_abstention_rate", "citation_validity", "p50_latency_ms", "p95_latency_ms")), f"faithfulness={e2e.get('faithfulness')}, citation={e2e.get('citation_validity')}, p95={e2e.get('p95_latency_ms')} ms")
        check("B / full suite artifacts", file_exists("eval/results/suite_20261126T155753Z.md") and file_exists("eval/results/suite_20261126T155753Z.json"), "timestamped JSON and Markdown summary")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        check("B / module-component-e2e suite", False, f"cannot validate suite: {exc}")

    try:
        with (ROOT / "eval" / "judge_labels.csv").open(encoding="utf-8-sig", newline="") as f:
            labels = [row for row in csv.DictReader(f) if (row.get("my_label") or "").strip()]
        agreement = read_json(result("judge_agreement_20261126T162229Z.json"))
        check("B / judge agreement labels", len(labels) >= 8 and agreement.get("filled_labels", 0) >= 8 and agreement.get("agreement_rate") is not None and agreement.get("cohen_kappa") is not None, f"filled labels={len(labels)}, agreement={agreement.get('agreement_rate')}, kappa={agreement.get('cohen_kappa')}")
    except (OSError, ValueError, TypeError) as exc:
        check("B / judge agreement", False, f"cannot validate labels/result: {exc}")

    try:
        stochastic = read_json(result("stochasticity_20261126T081757Z.json"))
        comparisons = stochastic.get("comparison", {}).get("all_differences", [])
        nonzero = stochastic.get("comparison", {}).get("nonzero_differences", [])
        explained = all(str(row.get("explanation", "")).strip() for row in comparisons)
        check("B / two-run stochasticity report", bool(stochastic.get("run_1")) and bool(stochastic.get("run_2")) and isinstance(comparisons, list) and len(comparisons) >= 1 and explained, f"metric comparisons={len(comparisons)}, nonzero differences={len(nonzero)}, all explanations present={explained}")
    except (OSError, ValueError, TypeError) as exc:
        check("B / stochasticity report", False, f"cannot validate stochasticity report: {exc}")

    # Part C: configured baseline/candidate, both gate outcomes, and release decision.
    try:
        before = baseline_suite["runs"]
        after = candidate_suite["runs"]
        before_k = before["component_retrieval"].get("top_k")
        after_k = after["component_retrieval"].get("top_k")
        check("C1 / environment-only candidate comparison", before_k == 3 and after_k == 8 and file_exists("eval/results/C1_comparison.md"), f"TOP_K baseline={before_k}, candidate={after_k}; three-level comparison present")
        pass_text = result("C2_gate_pass.txt").read_text(encoding="utf-8")
        fail_text = result("C2_gate_fail.txt").read_text(encoding="utf-8")
        check("C2 / passing gate output", "Overall |  | PASS" in pass_text and pass_text.count("| PASS") >= 5, "all five release rules pass")
        check("C2 / deliberate failing gate output", "Overall |  | FAIL" in fail_text and "citation_validity_at_least_minimum" in fail_text and "| FAIL" in fail_text, "citation validity fails the deliberately bad candidate")
        release = result("C_release_decision.md").read_text(encoding="utf-8")
        check("C / release decision recorded", "RELEASE" in release and "Reject" in release, "TOP_K=8 released; TOP_K=1 / threshold 0.99 rejected")
        gate_cfg = (ROOT / "gate.yaml").read_text(encoding="utf-8")
        check("C / gate thresholds justified and stored", all(token in gate_cfg for token in ("0.02", "0.95", "0.90", "36500")), "recall, faithfulness, citation, and p95 thresholds present")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        check("C / release gate evidence", False, f"cannot validate C artifacts: {exc}")

    # Part D: trace schema, live API evidence, guardrail, and trace-only D5.
    required_trace_fields = {
        "trace_id", "timestamp", "user_query", "rewritten_query", "embedding_model", "embedding_version",
        "collection", "retrieved", "filters", "reranked_order", "prompt_hash", "prompt", "model", "params",
        "response", "citations", "guardrail_actions", "latency_ms", "cache_hit",
    }
    trace_files = ["traces/sample_run.jsonl", "traces/example.jsonl", "traces/e3_batch_b_sample.jsonl", "traces/d5_candidate_fail_sample.jsonl"]
    schema_ok = True
    trace_items: list[dict[str, Any]] = []
    trace_errors: list[str] = []
    for relative in trace_files:
        try:
            rows = trace_records(relative)
            if not rows:
                schema_ok = False
                trace_errors.append(f"{relative}: empty")
            for row in rows:
                trace_items.append(row)
                missing = required_trace_fields - row.keys()
                latency = row.get("latency_ms", {})
                missing_latency = {"embed", "retrieve", "rerank", "generate", "total"} - latency.keys()
                invalid_hash = hashlib.sha256(row.get("prompt", "").encode("utf-8")).hexdigest() != row.get("prompt_hash")
                if missing or missing_latency or invalid_hash:
                    schema_ok = False
                    trace_errors.append(f"{relative}: missing={sorted(missing)}, latency={sorted(missing_latency)}, prompt_hash_invalid={invalid_hash}")
                if not all({"chunk_id", "doc_id", "doc_version", "score"}.issubset(item) for item in row.get("retrieved", [])):
                    schema_ok = False
                    trace_errors.append(f"{relative}: retrieved entry incomplete")
        except (OSError, ValueError, TypeError) as exc:
            schema_ok = False
            trace_errors.append(f"{relative}: {exc}")
    check("D1 / real trace schema", schema_ok, "; ".join(trace_errors) if trace_errors else "all required fields, nested latency, retrieval fields, and prompt hashes validated")
    injection_trace = next((x for x in trace_items if x.get("guardrail_actions")), {})
    actions = injection_trace.get("guardrail_actions", [])
    check("D4 / injection guardrail trace", len(actions) >= 1 and all(a.get("action_taken") == "removed" and a.get("rule_name") and a.get("chunk_id") and a.get("doc_id") for a in actions), f"guardrail actions={len(actions)}; removed chunk represented in trace")
    api_run = result("D1D4_api_run.txt").read_text(encoding="utf-8-sig") if result("D1D4_api_run.txt").exists() else ""
    check("D1 / API endpoint and metrics run", all(x in api_run for x in ("GET /health", "GET /metrics", "queries_total 3", "cache_hits_total 1", "injections_flagged_total 1")), "health and metrics captured from three local query requests")
    api_source = (ROOT / "rag" / "api.py").read_text(encoding="utf-8")
    check("D1 / query, health, and metrics routes", all(route in api_source for route in ("/query", "/health", "/metrics")), "all required API routes are defined")
    try:
        d5_text = result("D5_root_cause.md").read_text(encoding="utf-8")
        d5_rows = trace_records("traces/d5_candidate_fail_sample.jsonl")
        d5_id = d5_rows[0].get("trace_id") if len(d5_rows) == 1 else None
        rca = re.search(r"## Root cause analysis \(exactly five lines\)(.*?)(?:\n## |\Z)", d5_text, re.S)
        rca_lines = re.findall(r"^\d+\. .+", rca.group(1), re.M) if rca else []
        d5_ok = bool(d5_id) and d5_id in d5_text and len(rca_lines) == 5 and all(f'"{field}"' in d5_text for field in ("trace_id", "user_query", "retrieved[0]", "filters", "response", "citations"))
        check("D5 / trace-only diagnosis", d5_ok, f"matching trace id={d5_id}; root-cause lines={len(rca_lines)}")
    except (OSError, ValueError, TypeError) as exc:
        check("D5 / trace-only diagnosis", False, str(exc))
    m2("D2 / trace inspection CLI", "Member 2 owns the trace inspection tool; no Member 1 implementation claimed")

    # Part E: Batch B drift completed; live coverage tasks belong to Member 2.
    try:
        before_e3 = suite("suite_20261126T102138Z.json")
        after_e3 = suite("suite_20261126T105501Z.json")
        e3_text = result("E3_drift.md").read_text(encoding="utf-8")
        e3_ok = (
            before_e3.get("dataset", {}).get("questions") == after_e3.get("dataset", {}).get("questions") == 43
            and "Retrieval.clean.recall_at_5" in e3_text
            and "End-to-end.citation_validity" in e3_text
            and "traces/e3_batch_b_sample.jsonl" in e3_text
        )
        check("E3 / before-after Batch B report", e3_ok, "43-question suite comparison, metric table, and injection trace evidence are present")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        check("E3 / drift evidence", False, f"cannot validate E3 artifacts: {exc}")
    m2("E1 / live-query set", "Member 2 owns the live-query script and report; 40-query in-domain/uncovered classification remains to be supplied")
    m2("E2 / query coverage", "Member 2 owns coverage scoring and threshold report; uncovered-topic evidence remains to be supplied")
    m2("E4 / close the coverage gap", "Member 2 owns coverage workflow; add at least six coverage questions and show the before/after coverage result")

    # Confirm the evidence expected by the report is actually committed.
    required_tracked = [
        "eval/results/A_demo_log.txt", "eval/results/verification_20261126T102215Z-326500.json",
        "eval/results/suite_20261126T155753Z.json", "eval/results/suite_20261126T161600Z.json",
        "eval/results/suite_20261126T162002Z.json", "eval/results/C1_comparison.md",
        "eval/results/C2_gate_pass.txt", "eval/results/C2_gate_fail.txt",
        "eval/results/C_release_decision.md", "eval/results/D1D4_api_run.txt",
        "eval/results/D5_root_cause.md", "eval/results/E3_drift.md",
        "eval/results/stochasticity_20261126T081757Z.json", "eval/results/judge_agreement_20261126T162229Z.json",
        "traces/example.jsonl", "traces/sample_run.jsonl", "traces/e3_batch_b_sample.jsonl",
        "traces/d5_candidate_fail_sample.jsonl",
    ]
    not_tracked = [p for p in required_tracked if p not in tracked]
    check("A-E / result and trace evidence committed", not not_tracked, "all required result files are tracked" if not not_tracked else "untracked/missing: " + ", ".join(not_tracked))

    # Scan committed text and names for actual credentials; .env.example is safe.
    env_files = [p for p in tracked if Path(p).name == ".env"]
    secret_patterns = [
        re.compile(r"\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16})\b"),
        re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
        re.compile(r"(?i)\b(?:api[_ -]?key|secret|token)\b\s*[:=]\s*['\"]?([A-Za-z0-9_+/=-]{24,})"),
    ]
    found_secrets: list[str] = []
    for relative in tracked:
        path = ROOT / relative
        if not path.is_file():
            continue
        try:
            content = path.read_bytes().decode("utf-8", errors="ignore")
        except OSError:
            continue
        if any(pattern.search(content) for pattern in secret_patterns):
            found_secrets.append(relative)
    check("Security / no .env or committed API keys", not env_files and not found_secrets, "no tracked .env or credential-like values found" if not env_files and not found_secrets else f".env={env_files}; secret-like content={found_secrets}")

    failures = sum(status == "FAIL" for status, _, _ in checks)
    m2_count = sum(status == "M2" for status, _, _ in checks)
    print("RAGOps Parts A-E repository audit")
    print("STATUS | CHECK | EVIDENCE")
    print("-------|-------|---------")
    for status, name, detail in checks:
        print(f"{status:4} | {name} | {detail}")
    print(f"\nSummary: {len(checks) - failures - m2_count} PASS, {failures} FAIL, {m2_count} M2-owned items")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
