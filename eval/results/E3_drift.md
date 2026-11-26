# E3 — Batch B drift

Before: `suite_20261126T102138Z` (E3-before-Batch-B, collection `e3-before-b-500`).
After: `suite_20261126T105501Z` (E3-after-Batch-B-C1-baseline500, collection `e3-before-b-500`).

Positive deltas mean the after/candidate value increased. Latency and determinism values are measurements, not quality scores.

| Level / metric | Before | After | Delta (after − before) |
| --- | ---: | ---: | ---: |
| Embedding.determinism_largest_absolute_difference | 0 | 0 | 0 |
| Embedding.embedding_time_per_chunk_ms | 50.981022 | 34.605817 | -16.375205 |
| Embedding.mean_paraphrase_cosine | 0.48697 | 0.48697 | 0 |
| Embedding.mean_unrelated_cosine | 0.01636 | 0.01636 | 0 |
| Embedding.pair_embedding_elapsed_ms | 546.518 | 392.539 | -153.979 |
| Embedding.paraphrase_pairs | 15 | 15 | 0 |
| Embedding.seed | 4,032.000 | 4,032.000 | 0 |
| Embedding.similarity_gap | 0.47061 | 0.47061 | 0 |
| Embedding.timed_active_chunks | 36 | 54 | 18 |
| Embedding.unrelated_pairs | 15 | 15 | 0 |
| End-to-end.abstention_correctness | 1 | 1 | 0 |
| End-to-end.answer_expected_count | 36 | 36 | 0 |
| End-to-end.citation_evaluable_count | 36 | 36 | 0 |
| End-to-end.citation_valid_count | 33 | 35 | 2 |
| End-to-end.citation_validity | 0.916667 | 0.972222 | 0.055555 |
| End-to-end.correct_abstentions | 7 | 7 | 0 |
| End-to-end.faithfulness | 1 | 1 | 0 |
| End-to-end.faithfulness_answered_only | 1 | 1 | 0 |
| End-to-end.faithfulness_scored_questions | 43 | 43 | 0 |
| End-to-end.false_abstention_rate | 0.083333 | 0.027778 | -0.055555 |
| End-to-end.false_abstentions | 3 | 1 | -2 |
| End-to-end.llm_judge_calls | 33 | 35 | 2 |
| End-to-end.mean_judge_latency_ms | 8,440.163 | 6,704.096 | -1,736.067 |
| End-to-end.p50_latency_ms | 16,187.882 | 14,461.766 | -1,726.116 |
| End-to-end.p95_latency_ms | 30,996.301 | 27,459.989 | -3,536.312 |
| End-to-end.query_count | 43 | 43 | 0 |
| End-to-end.unanswerable_count | 7 | 7 | 0 |
| End-to-end.vacuous_truth_abstentions | 10 | 8 | -2 |
| Retrieval delta vs clean.noise_documents.mrr | 0 | 0 | 0 |
| Retrieval delta vs clean.noise_documents.ndcg_at_5 | 0 | 0 | 0 |
| Retrieval delta vs clean.noise_documents.recall_at_3 | 0 | 0 | 0 |
| Retrieval delta vs clean.noise_documents.recall_at_5 | 0 | 0 | 0 |
| Retrieval delta vs clean.typo_queries.mrr | -0.067592 | -0.088889 | -0.021297 |
| Retrieval delta vs clean.typo_queries.ndcg_at_5 | -0.057459 | -0.088767 | -0.031308 |
| Retrieval delta vs clean.typo_queries.recall_at_3 | -0.069445 | -0.069444 | 0.000001 |
| Retrieval delta vs clean.typo_queries.recall_at_5 | -0.027778 | -0.083333 | -0.055555 |
| Retrieval.clean.mrr | 0.756944 | 0.83287 | 0.075926 |
| Retrieval.clean.ndcg_at_5 | 0.772112 | 0.853492 | 0.08138 |
| Retrieval.clean.recall_at_3 | 0.805556 | 0.861111 | 0.055555 |
| Retrieval.clean.recall_at_5 | 0.847222 | 0.958333 | 0.111111 |
| Retrieval.noise_documents.mrr | 0.756944 | 0.83287 | 0.075926 |
| Retrieval.noise_documents.ndcg_at_5 | 0.772112 | 0.853492 | 0.08138 |
| Retrieval.noise_documents.recall_at_3 | 0.805556 | 0.861111 | 0.055555 |
| Retrieval.noise_documents.recall_at_5 | 0.847222 | 0.958333 | 0.111111 |
| Retrieval.typo_queries.mrr | 0.689352 | 0.743981 | 0.054629 |
| Retrieval.typo_queries.ndcg_at_5 | 0.714653 | 0.764725 | 0.050072 |
| Retrieval.typo_queries.recall_at_3 | 0.736111 | 0.791667 | 0.055556 |
| Retrieval.typo_queries.recall_at_5 | 0.819444 | 0.875 | 0.055556 |


## Run and corpus details

Both suites used seed 4032, the same 43-question golden set, collection `e3-before-b-500`, `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`, `TOP_K=5`, `SIMILARITY_THRESHOLD=0.28`, and the cached local models in offline mode. Before Batch B, `EVAL_ALLOW_MISSING_GROUND_TRUTH=1` counted Batch-B-only pages as absent; after Batch B, `EVAL_ALLOW_GROUND_TRUTH_DRIFT=1` allowed the fixed doc/page retrieval metrics to run while recording superseded-answer mismatches as unverified.

The actual Batch B ingestion report is `verification_20261126T102215Z-326500.json`: 14 discovered, 8 passed, 6 quarantined, 6 new documents, 2 updated documents, 18 new chunks, 6 replacement chunks, and 24 embedded chunks. It archived `verification-standard` v2.1 and `versioning-standard` v1.2. The newer verification standard changed the active near-duplicate threshold from 0.94 to 0.91; q06's expected 0.94 fact is stale against the active source, although the token-overlap validator partially matches it. q07 is explicitly marked unverified because the active v1.3 reference answer differs from the old version. Version 1.3 of the versioning standard is active and its older vectors are excluded by the active-status filter.

The two exact duplicate files and the near-duplicate file were quarantined, as were the corrupt, truncated, and missing-metadata fixtures. They contributed no active retrieval vectors. Batch B added clean material including the repair, feedback, injection, latency, review, provenance, verification, and versioning records.

The after-Batch-B q23 trace is `997a2785-9c11-4d6c-8e83-e0300a6e2ce0` and is preserved in `traces/e3_batch_b_sample.jsonl`. Its three guardrail actions (`ignore_previous_instructions`, `reveal_system_prompt`, and `api_key_exfiltration`) all removed the planted injection chunk before prompt construction; the injected instruction text is absent from the prompt. The trace preserves the generated response and its citations for review. The response is context-supported but does not directly answer q23, showing that the faithfulness metric alone does not measure question-answer relevance. The before run could not retrieve `injection-test-record` because that document did not yet exist in Batch A.
