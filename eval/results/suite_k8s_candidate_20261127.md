# RAGOps evaluation suite — 2026-11-27T07:33:58.011533+00:00

- Collection: `cand_topk8`
- Seed: `4032`
- Label: candidate-topk8
- Golden questions: 49 (36 answerable, 13 unanswerable, 9 hard)

## Module and component metrics

| Evaluation | Metric | Value |
| --- | --- | ---: |
| Embedding | Mean paraphrase cosine | 0.486970 |
| Embedding | Mean unrelated cosine | 0.016360 |
| Embedding | Similarity gap | 0.470610 |
| Embedding | Time per chunk (ms) | 33.0966 |
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
| False-abstention rate | 0.027778 |
| Citation validity | 0.972222 |
| Query latency p50 (ms) | 32239.514 |
| Query latency p95 (ms) | 70173.700 |
| Mean judge latency (ms) | 10836.023 |
| Local LLM judge calls | 35 |
| Canonical abstentions scored as no factual claims | 14 |

## Release gate

- Result: **SKIPPED**

| Check | Passed |
| --- | --- |

Gate values: `{}`
