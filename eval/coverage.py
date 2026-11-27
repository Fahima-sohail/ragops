"""Score live-query coverage against golden questions with local embeddings."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from rag.config import ROOT, get_settings
from rag.embeddings import embed_texts
from eval.golden import load_golden


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_golden(path: Path) -> list[dict]:
    if path.resolve() == (ROOT / "eval" / "golden.jsonl").resolve():
        return load_golden(path, include_human_drafts=False)[0]
    return read_jsonl(path)


def score(queries: list[dict], golden: list[dict], threshold: float, model: str) -> dict:
    if not queries or not golden:
        raise ValueError("coverage needs at least one live query and one golden question")
    q_vectors, _ = embed_texts([row["query"] for row in queries], model)
    g_vectors, _ = embed_texts([row["question"] for row in golden], model)
    uncovered = []
    covered = 0
    by_domain: dict[str, list[float]] = defaultdict(list)
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for query, vector in zip(queries, q_vectors):
        similarities = [sum(a * b for a, b in zip(vector, candidate)) for candidate in g_vectors]
        best_index = max(range(len(similarities)), key=similarities.__getitem__)
        best_score = float(similarities[best_index])
        domain = "in_domain" if query["expected_domain"] else "out_of_domain"
        by_domain[domain].append(best_score)
        record = {
            "id": query["id"],
            "query": query["query"],
            "topic": query["topic"],
            "expected_domain": bool(query["expected_domain"]),
            "nearest_golden_id": golden[best_index]["id"],
            "nearest_golden_question": golden[best_index]["question"],
            "similarity": round(best_score, 6),
        }
        if best_score >= threshold:
            covered += 1
        else:
            uncovered.append(record)
            by_topic[str(query["topic"])].append(record)
    total = len(queries)
    return {
        "query_count": total,
        "covered_count": covered,
        "coverage": covered / total,
        "threshold": threshold,
        "domain_coverage": {
            key: {"count": len(values), "covered": sum(value >= threshold for value in values), "coverage": sum(value >= threshold for value in values) / len(values)}
            for key, values in sorted(by_domain.items())
        },
        "uncovered_queries": uncovered,
        "uncovered_topics": {topic: len(rows) for topic, rows in sorted(by_topic.items())},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", type=Path, default=ROOT / "eval" / "live_queries.jsonl")
    parser.add_argument("--golden", type=Path, default=ROOT / "eval" / "golden.jsonl")
    parser.add_argument("--additions", type=Path, help="score a second time with these questions appended")
    parser.add_argument("--threshold", type=float, default=0.55, help="cosine similarity coverage floor")
    parser.add_argument("--minimum", type=float, default=0.85, help="minimum overall coverage required")
    parser.add_argument("--output", type=Path, default=ROOT / "eval" / "results" / "coverage.json")
    args = parser.parse_args(argv)
    if not 0 <= args.threshold <= 1 or not 0 <= args.minimum <= 1:
        parser.error("thresholds must be in [0, 1]")
    try:
        queries = read_jsonl(args.live)
        golden = read_golden(args.golden)
        settings = get_settings()
        before = score(queries, golden, args.threshold, settings.embed_model)
        report = {"timestamp": datetime.now(timezone.utc).isoformat(), "embedding_model": settings.embed_model, "method": "maximum cosine similarity between each live query and golden question", "justification": "A query is flagged below 0.55 cosine; the overall target is 85%, following the assignment's coverage example.", "before": before}
        if args.additions:
            extra = read_jsonl(args.additions)
            after = score(queries, golden + extra, args.threshold, settings.embed_model)
            report["additions_count"] = len(extra)
            report["after"] = after
            report["coverage_change"] = after["coverage"] - before["coverage"]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Coverage threshold: {args.threshold:.2f}; required overall: {args.minimum:.0%}")
        for label in ("before", "after"):
            if label in report:
                section = report[label]
                print(f"{label.title()}: {section['covered_count']}/{section['query_count']} ({section['coverage']:.1%})")
                print(f"Uncovered queries: {len(section['uncovered_queries'])}; topics: {section['uncovered_topics']}")
        print(f"Coverage report: {args.output}")
        release_coverage = report.get("after", before)
        return 0 if release_coverage["coverage"] >= args.minimum else 1
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        print(f"coverage analysis failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
