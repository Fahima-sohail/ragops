---
doc_id: citations-abstention
source: Aster Research Lab policy archive (fictional test corpus)
title: Citation and Abstention Standard
version: 1.0
date: 2026-11-01
page_count: 3
---

## Page 1

A grounded response cites the retrieved document title, version, and page number. The structured citation must refer to a chunk that was actually retrieved for that request. A citation to a document found elsewhere in the corpus is invalid if that document was not part of the prompt context. The generator should make the answer short enough that each factual statement can be checked against one or more cited passages.

## Page 2

The service abstains when retrieval provides no evidence for the requested fact, when the relevant passage was withheld by a guardrail, or when the answer depends on personal or live information absent from the archive. The standard abstention says that the archive does not contain enough information to answer reliably. An abstention has no factual citation and is counted separately from an empty response or a server error.

## Page 3

Citation validity is evaluated against the retrieved document id, version, and page. An answer may cite multiple passages when the conclusion needs more than one source. The evaluator records whether every cited location exists, whether each citation was retrieved, and whether the cited passage supports the claim. A response that includes an unsupported claim with a valid citation still fails faithfulness.
