---
doc_id: evaluation-protocol
source: Aster Research Lab policy archive (fictional test corpus)
title: Offline Evaluation Protocol
version: 1.2
date: 2026-11-01
page_count: 3
---

## Page 1

The golden set contains at least twenty-five questions: fifteen answerable questions with a document and page, five questions that should be unanswerable, and five hard questions that use paraphrases, multiple chunks, or the second batch. Each item records whether its wording is human or synthetic, its review state, its answerability, and its relevant document and page. Questions are reviewed for ambiguity before their labels are final.

## Page 2

The embedding module check compares at least fifteen paraphrase pairs with at least fifteen unrelated pairs. It records mean cosine similarity for each group, their gap, embedding time per chunk, and the largest difference when the same text is embedded twice. The retrieval check records recall at three and five, MRR, nDCG at five, and the change after a noise test. The end-to-end check records faithfulness, correct abstentions, citation validity, and p50 and p95 latency.

## Page 3

A fixed random seed controls question order, noise selection, and any randomized candidate generation. The complete suite runs twice. The result contains both run summaries and the per-metric difference. Remaining generation variation is reported rather than hidden. If an LLM judge is used for faithfulness, at least eight answers are independently labelled by a person and judge agreement is calculated from those reviewed pairs.
