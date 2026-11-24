---
doc_id: incident-recovery
source: Aster Research Lab policy archive (fictional test corpus)
title: Incident and Recovery Runbook
version: 1.3
date: 2026-11-01
page_count: 3
---

## Page 1

A retrieval incident begins when the API is healthy but returns missing evidence, stale versions, invalid citations, or unexpected abstentions. The operator captures the trace id, checks the collection and embedding version, and reads the exact retrieval filter and ranked chunks. If the source is stale, the ingestion job is run against a reviewed batch. If a document is corrupt or incomplete, it stays in quarantine until corrected.

## Page 2

If a new document revision causes a regression, the operator restores the last known good version by document id and version. The ingestion job is the only writer and records the rollback. The operator then submits a test question that targets the affected clause and checks that the returned trace shows the expected active version. A successful health check alone does not prove that retrieval has recovered.

## Page 3

After an incident, the owner updates the verification report, the evaluation result, and the decision record. A source-specific extraction problem needs a fixture or a parser correction. A prompt-injection event needs a guardrail test. A missing coverage topic becomes a proposed golden question only after review. The incident record identifies the observed symptom, trace evidence, repair, and regression check.
