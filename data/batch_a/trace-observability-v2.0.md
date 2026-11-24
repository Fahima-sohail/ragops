---
doc_id: trace-observability
source: Aster Research Lab policy archive (fictional test corpus)
title: Trace and Observability Standard
version: 2.0
date: 2026-11-01
page_count: 3
---

## Page 1

Every query writes one JSON line with a trace id and UTC timestamp. The record includes the original and rewritten query, embedding model and version, collection, retrieved chunk ids, document ids and versions, scores, filters, reranked order, prompt hash, prompt text, model, parameters, response, citations, guardrail actions, stage latencies, and cache hit status. The JSON line is emitted to standard output and appended under TRACE_DIR.

## Page 2

Latency values cover embedding, retrieval, reranking, generation, and total request time in milliseconds. The top-one similarity distribution, abstention rate, cache hit rate, per-stage p95 latency, and count of injection attempts are summarized from traces over a requested time window. The metrics endpoint reports current process counters and a health status without changing the vector collection.

## Page 3

The trace inspection tool is owned by Member 2. It takes a trace id and displays the exact prompt and retrieved context. A root-cause write-up must use only that trace to identify the incorrect document version, missing chunk, filter, or other recorded cause. Trace records are treated as sensitive because they can include user questions and prompts; retention follows the storage policy.
