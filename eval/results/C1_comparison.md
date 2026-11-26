# C1 — TOP_K=3 baseline vs TOP_K=8 candidate

Before: `suite_20261126T155753Z` (C1-C2-baseline-topk3, collection `e3-before-b-500`).
After: `suite_20261126T161600Z` (C1-C2-candidate-topk8, collection `cand_topk8`).

Positive deltas mean the after/candidate value increased. Latency and determinism values are measurements, not quality scores.

| Level / metric | Before | After | Delta (after − before) |
| --- | ---: | ---: | ---: |
| Embedding.determinism_largest_absolute_difference | 0 | 0 | 0 |
| Embedding.embedding_time_per_chunk_ms | 39.752011 | 33.942552 | -5.809459 |
| Embedding.mean_paraphrase_cosine | 0.48697 | 0.48697 | 0 |
| Embedding.mean_unrelated_cosine | 0.01636 | 0.01636 | 0 |
| Embedding.pair_embedding_elapsed_ms | 408.563 | 385.521 | -23.042 |
| Embedding.paraphrase_pairs | 15 | 15 | 0 |
| Embedding.seed | 4,032.000 | 4,032.000 | 0 |
| Embedding.similarity_gap | 0.47061 | 0.47061 | 0 |
| Embedding.timed_active_chunks | 54 | 54 | 0 |
| Embedding.unrelated_pairs | 15 | 15 | 0 |
| End-to-end.abstention_correctness | 1 | 1 | 0 |
| End-to-end.answer_expected_count | 36 | 36 | 0 |
| End-to-end.citation_evaluable_count | 36 | 36 | 0 |
| End-to-end.citation_valid_count | 32 | 35 | 3 |
| End-to-end.citation_validity | 0.888889 | 0.972222 | 0.083333 |
| End-to-end.correct_abstentions | 7 | 7 | 0 |
| End-to-end.faithfulness | 1 | 1 | 0 |
| End-to-end.faithfulness_answered_only | 1 | 1 | 0 |
| End-to-end.faithfulness_scored_questions | 43 | 43 | 0 |
| End-to-end.false_abstention_rate | 0.111111 | 0.027778 | -0.083333 |
| End-to-end.false_abstentions | 4 | 1 | -3 |
| End-to-end.llm_judge_calls | 32 | 35 | 3 |
| End-to-end.mean_judge_latency_ms | 6,020.720 | 6,282.799 | 262.079 |
| End-to-end.p50_latency_ms | 12,132.882 | 14,451.687 | 2,318.805 |
| End-to-end.p95_latency_ms | 30,392.909 | 27,204.269 | -3,188.640 |
| End-to-end.query_count | 43 | 43 | 0 |
| End-to-end.unanswerable_count | 7 | 7 | 0 |
| End-to-end.vacuous_truth_abstentions | 11 | 8 | -3 |
| Retrieval delta vs clean.noise_documents.mrr | 0 | 0 | 0 |
| Retrieval delta vs clean.noise_documents.ndcg_at_5 | 0 | 0 | 0 |
| Retrieval delta vs clean.noise_documents.recall_at_3 | 0 | 0 | 0 |
| Retrieval delta vs clean.noise_documents.recall_at_5 | 0 | 0 | 0 |
| Retrieval delta vs clean.typo_queries.mrr | -0.088889 | -0.088889 | 0 |
| Retrieval delta vs clean.typo_queries.ndcg_at_5 | -0.088767 | -0.088767 | 0 |
| Retrieval delta vs clean.typo_queries.recall_at_3 | -0.069444 | -0.069444 | 0 |
| Retrieval delta vs clean.typo_queries.recall_at_5 | -0.083333 | -0.083333 | 0 |
| Retrieval.clean.mrr | 0.83287 | 0.83287 | 0 |
| Retrieval.clean.ndcg_at_5 | 0.853492 | 0.853492 | 0 |
| Retrieval.clean.recall_at_3 | 0.861111 | 0.861111 | 0 |
| Retrieval.clean.recall_at_5 | 0.958333 | 0.958333 | 0 |
| Retrieval.noise_documents.mrr | 0.83287 | 0.83287 | 0 |
| Retrieval.noise_documents.ndcg_at_5 | 0.853492 | 0.853492 | 0 |
| Retrieval.noise_documents.recall_at_3 | 0.861111 | 0.861111 | 0 |
| Retrieval.noise_documents.recall_at_5 | 0.958333 | 0.958333 | 0 |
| Retrieval.typo_queries.mrr | 0.743981 | 0.743981 | 0 |
| Retrieval.typo_queries.ndcg_at_5 | 0.764725 | 0.764725 | 0 |
| Retrieval.typo_queries.recall_at_3 | 0.791667 | 0.791667 | 0 |
| Retrieval.typo_queries.recall_at_5 | 0.875 | 0.875 | 0 |


## Configuration and measured context size

Both suites used `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`, `SIMILARITY_THRESHOLD=0.28`, seed 4032, the same 43 questions, the same Batch A + Batch B snapshot, and offline cached models. The baseline used collection `e3-before-b-500` with TOP_K=3; the candidate used `cand_topk8` with TOP_K=8. No application code or other retrieval setting changed.

Mean retrieved chunks per golden question were 3.000 for baseline and 8.000 for candidate (delta +5.000). The component metrics cover clean retrieval, a three-document temporary noise collection, and seeded typo queries. The end-to-end metrics include answers, judge faithfulness, abstentions, citation checks, and latency. Full raw results: `suite_20261126T155753Z.json` and `suite_20261126T161600Z.json`.
