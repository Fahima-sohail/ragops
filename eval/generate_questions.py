"""Generate candidate synthetic golden questions from active indexed pages."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import sys
from typing import Any

from eval.golden import active_page_texts
from eval.seeding import seed_all
from rag.config import ROOT, get_settings
from rag.llm import generate

ANSWERABLE_PAGE_GROUPS = [
    [("service-charter", 2), ("intake-standard", 3)],
    [("verification-standard", 1), ("verification-standard", 3)],
    [("prompt-safety", 2), ("injection-test-record", 3)],
    [("retrieval-quality", 2), ("retrieval-quality", 3)],
    [("document-repair", 3), ("feedback-loop", 3)],
    [("release-gate", 1), ("storage-backup", 1)],
]


def _write(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _label(ref: tuple[str, int], settings) -> dict[str, Any]:
    from rag.store import open_read_collection

    _, collection = open_read_collection(settings)
    found = collection.get(
        where={"$and": [{"doc_id": ref[0]}, {"page": ref[1]}, {"status": "active"}]},
        include=["metadatas"],
    )
    versions = sorted({str(row.get("doc_version", "unknown")) for row in found.get("metadatas", []) if row})
    return {"doc_id": ref[0], "page": ref[1], "versions": versions}


def generate_candidates(max_new_tokens: int = 220) -> Path:
    settings = get_settings(llm_api_key="")  # force cached local inference; never call a remote API
    seed_all(settings.seed)
    pages = active_page_texts(settings)
    groups = [group for group in ANSWERABLE_PAGE_GROUPS if all(ref in pages for ref in group)]
    if len(groups) != len(ANSWERABLE_PAGE_GROUPS):
        absent = [ref for group in ANSWERABLE_PAGE_GROUPS for ref in group if ref not in pages]
        raise ValueError(f"generation pages must be present in the active indexed collection: {absent}")
    order = list(range(len(groups)))
    random.Random(settings.seed).shuffle(order)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = ROOT / "eval" / "results" / f"golden_generation_{stamp}.json"
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": settings.seed,
        "collection": settings.collection,
        "embedding_model": settings.embed_model,
        "llm_model": settings.llm_model,
        "generation_mode": "local cached model; remote API disabled",
        "answerable_candidate_runs": [],
        "hard_candidate_run": None,
        "unanswerable_candidate_run": None,
    }
    _write(path, payload)

    for group_index in order:
        refs = groups[group_index]
        evidence = "\n\n".join(
            f"SOURCE {doc_id} PAGE {page}\n{pages[(doc_id, page)]}"
            for doc_id, page in refs
        )
        prompt = (
            "Create one answerable synthetic question from the evidence below. "
            "Return a compact JSON object with keys question, reference_answer, and evidence_quote. "
            "The evidence_quote must be copied exactly from one source page. Keep each answer a short phrase "
            "or one sentence; do not make up details. Return only a JSON array.\n\n" + evidence
        )
        raw = generate(prompt, settings, max_new_tokens=max_new_tokens)
        run = {
            "source_pages": [_label(ref, settings) for ref in refs],
            "prompt": prompt,
            "raw_model_output": raw,
        }
        payload["answerable_candidate_runs"].append(run)
        _write(path, payload)
        print(json.dumps({"candidate_run": group_index + 1, "saved": str(path), "raw_model_output": raw}, ensure_ascii=False), flush=True)

    hard_refs = [("versioning-standard", 3), ("incident-recovery", 2)]
    hard_evidence = "\n\n".join(
        f"SOURCE {doc_id} PAGE {page}\n{pages[(doc_id, page)]}" for doc_id, page in hard_refs
    )
    hard_prompt = (
        "Create exactly one hard, answerable question that requires combining both source passages. "
        "Return one compact JSON object with question, reference_answer, and evidence_quote_1/evidence_quote_2. "
        "Each evidence quote must be an exact substring of its corresponding passage. Return JSON only.\n\n" + hard_evidence
    )
    payload["hard_candidate_run"] = {
        "source_pages": [_label(ref, settings) for ref in hard_refs],
        "prompt": hard_prompt,
        "raw_model_output": generate(hard_prompt, settings, max_new_tokens=max_new_tokens),
    }
    _write(path, payload)
    print(json.dumps({"candidate_run": "hard", "saved": str(path), "raw_model_output": payload["hard_candidate_run"]["raw_model_output"]}, ensure_ascii=False), flush=True)

    unanswerable_ref = ("citations-abstention", 2)
    unanswerable_prompt = (
        "Using the policy below, propose one synthetic question asking for a specific personal or live fact "
        "that the indexed archive does not contain. Ask for the missing fact itself, not for the policy on how to handle it. "
        "For example, ask for a current private phone number, not what the service says about private data. "
        "Return JSON only with one key question. Do not answer the question.\n\n"
        f"SOURCE {unanswerable_ref[0]} PAGE {unanswerable_ref[1]}\n{pages[unanswerable_ref]}"
    )
    payload["unanswerable_candidate_run"] = {
        "source_pages": [_label(unanswerable_ref, settings)],
        "prompt": unanswerable_prompt,
        "raw_model_output": generate(unanswerable_prompt, settings, max_new_tokens=max_new_tokens),
    }
    _write(path, payload)
    print(json.dumps({"candidate_run": "unanswerable", "saved": str(path), "raw_model_output": payload["unanswerable_candidate_run"]["raw_model_output"]}, ensure_ascii=False), flush=True)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-new-tokens", type=int, default=220)
    args = parser.parse_args(argv)
    try:
        if args.max_new_tokens < 32:
            raise ValueError("--max-new-tokens must be at least 32")
        result = generate_candidates(args.max_new_tokens)
        print(json.dumps({"generation_result": str(result)}, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
