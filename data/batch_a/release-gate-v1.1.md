---
doc_id: release-gate
source: Aster Research Lab policy archive (fictional test corpus)
title: Candidate Release Gate
version: 1.1
date: 2026-11-01
page_count: 3
---

## Page 1

A candidate changes one selected pipeline setting while all other settings remain fixed. The baseline and candidate use the same corpus, golden set, random seed, embedding model, and judge procedure. The report compares embedding behavior, retrieval metrics, end-to-end quality, and latency. The candidate JSON records the settings and result path so the gate can be replayed without relying on an untracked notebook.

## Page 2

The default gate rejects a recall-at-five drop greater than two percentage points, faithfulness below 0.50, a p95 latency above 30,000 milliseconds, or abstention correctness below the baseline. Faithfulness uses a disclosed retrieval-reference and citation check, not an LLM judge. The latency ceiling accounts for a small local CPU model. Thresholds are read from gate.yaml, not embedded in the API image. A deliberately poor candidate is retained as a failing example and a passing candidate is also retained with its evidence. The gate exits with status one on failure.

## Page 3

A passing local gate is necessary but not sufficient for deployment. Member 2 owns Kubernetes rollout and rollback evidence. The candidate collection remains isolated until the Kubernetes evaluation Job passes. Operators record the chosen release or rejection, the exact baseline and candidate file names, and the relevant result paths. A rollback must make the previous collection and embedding version visible in a new trace.
