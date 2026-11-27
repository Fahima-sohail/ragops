# RAGOps evaluation suite — 2026-11-27T07:01:09.933401+00:00

- Collection: `e3-before-b-500`
- Seed: `4032`
- Label: (none)
- Golden questions: 49 (36 answerable, 13 unanswerable, 9 hard)

## Module and component metrics

| Evaluation | Metric | Value |
| --- | --- | ---: |
| Embedding | Mean paraphrase cosine | 0.486970 |
| Embedding | Mean unrelated cosine | 0.016360 |
| Embedding | Similarity gap | 0.470610 |
| Embedding | Time per chunk (ms) | 38.0212 |
| Retrieval (clean) | Recall@3 | 0.861111 |
| Retrieval (clean) | Recall@5 | 0.958333 |
| Retrieval (clean) | MRR | 0.832870 |
| Retrieval (clean) | nDCG@5 | 0.853492 |
| Retrieval (noise_documents) | Recall@3 | 0.861111 |
| Retrieval (noise_documents) | Recall@5 | 0.958333 |
| Retrieval (noise_documents) | MRR | 0.832870 |
| Retrieval (noise_documents) | nDCG@5 | 0.853492 |
| Retrieval (typo_queries) | Recall@3 | 0.791667 |
| Retrieval (typo_queries) | Recall@5 | 0.875000 |
| Retrieval (typo_queries) | MRR | 0.743981 |
| Retrieval (typo_queries) | nDCG@5 | 0.764725 |

## End-to-end metrics

| Metric | Value |
| --- | ---: |
| Faithfulness (LLM judge mean) | 1.000000 |
| Correct abstention rate | 1.000000 |
| False-abstention rate | 0.111111 |
| Citation validity | 0.888889 |
| Query latency p50 (ms) | 35774.512 |
| Query latency p95 (ms) | 91226.900 |
| Mean judge latency (ms) | 10689.881 |
| Local LLM judge calls | 32 |
| Canonical abstentions scored as no factual claims | 17 |

## Release gate

- Result: **FAIL**

| Check | Passed |
| --- | --- |
| recall_at_5_drop_within_limit | yes |
| faithfulness_at_least_minimum | yes |
| citation_validity_at_least_minimum | no |
| p95_latency_within_limit | no |
| abstention_correctness_not_below_baseline | yes |

Gate values: `{"baseline_abstention_correctness": 1.0, "baseline_recall_at_5": 0.958333, "candidate_abstention_correctness": 1.0, "candidate_recall_at_5": 0.958333, "citation_validity": 0.888889, "faithfulness": 1.0, "maximum_p95_latency_ms": 36500.0, "minimum_citation_validity": 0.9, "minimum_faithfulness": 0.95, "p95_latency_ms": 91226.9, "recall_drop": 0.0}`
