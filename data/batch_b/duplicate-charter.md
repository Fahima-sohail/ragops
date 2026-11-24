---
doc_id: charter-copy-two
source: Aster Research Lab policy archive (fictional test corpus)
title: RAG Service Charter
version: 1.0
date: 2026-11-02
page_count: 3
---

## Page 1

The Aster Research Lab assistant answers operational questions from the controlled policy archive. It returns the source title, document version, and page with each supported answer. The service does not treat a fluent answer as evidence. A response without a supporting passage must be marked as an abstention. This charter applies to the sample deployment and does not establish policy for any real university or employer. The service owner reviews the source list before each release.

## Page 2

The service has four runtime stages: embed the query, retrieve active passages, assemble a bounded prompt, and generate a cited answer. Ingestion is a separate writer process. The API process may read the persistent collection but must never add, update, or delete vectors. Each response carries a trace identifier so an operator can locate the exact retrieved passages and prompt. A service restart must not remove the corpus or trace archive.

## Page 3

The service owner is accountable for the collection name, embedding model, language model, retrieval limit, and release decision. Operators record those values with evaluation results. A model change is a candidate until the evaluation gate passes. If the candidate fails, the previous collection remains active. Users should report missing or misleading evidence through the feedback register, not by asking the model to invent a policy answer.
