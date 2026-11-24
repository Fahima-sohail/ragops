---
doc_id: retrieval-quality
source: Aster Research Lab policy archive (fictional test corpus)
title: Retrieval Quality Standard
version: 1.3
date: 2026-11-01
page_count: 3
---

## Page 1

The retriever embeds the user question with the configured local Sentence Transformers model and searches the persistent Chroma collection. It returns at most TOP_K active chunks, ordered by cosine distance converted to similarity. Every result preserves chunk id, document id, version, title, source, page, and score. Superseded chunks and quarantined documents are excluded. A retrieval filter is recorded in the trace even when the filter is empty.

## Page 2

Recall at k measures whether at least one relevant document and page appears among the first k results. Mean reciprocal rank rewards a relevant item appearing near the top. Normalized discounted cumulative gain gives more credit to relevant results at earlier ranks. The evaluation reports recall at three and five, MRR, and nDCG at five. Each metric includes its query count and relevance definition so an operator can reproduce the calculation.

## Page 3

The noise check adds three unrelated test passages to a copy of the candidate ranking and measures the same retrieval metrics again. It does not write those passages to the production Chroma collection. A second check introduces deterministic query typos. The report records the absolute change from the clean run and keeps the random seed with the result file. A failed retrieval metric blocks candidate release even if generated answers sound convincing.
