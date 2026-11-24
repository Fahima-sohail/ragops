---
doc_id: latency-runbook
source: Aster Research Lab policy archive (fictional test corpus)
title: Latency and Load Runbook
version: 1.0
date: 2026-11-12
page_count: 3
---

## Page 1

The latency report separates embedding, retrieval, reranking, and generation time. The total includes request validation and trace writing. Percentiles are calculated over successful and abstained queries, while errors are listed separately. A slow generator must not be hidden by reporting only retrieval time.

## Page 2

The load test uses a fixed query list and a recorded concurrency level. It checks p50 and p95 latency, API error count, process memory, and the time needed to load local models. The evaluation gate uses the p95 threshold in gate.yaml. Resource requests and limits for Kubernetes are chosen from measurements made during the demo workload.

## Page 3

When latency exceeds the threshold, the operator checks model load time, request queueing, retrieved context size, and per-stage trace values. Increasing TOP_K can improve recall but also increases prompt length and generation time. Any candidate change must rerun the same suite so the quality and latency trade-off is visible.
