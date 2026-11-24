---
doc_id: verification-standard
source: Aster Research Lab policy archive (fictional test corpus)
title: Document Verification Standard
version: 2.2
date: 2026-11-13
page_count: 3
---

## Page 1

Quality verification rejects empty text, garbled extraction, or an extraction failure. The checker requires readable text and rejects documents when replacement characters or non-printing characters dominate. A text file ending halfway through a sentence is incomplete when the manifest also marks it truncated. The verifier records a separate pass or fail for quality, completeness, recency, and uniqueness, with a concise reason for each result.

## Page 2

Completeness verification requires source, title, a date or version, and page count. The declared page count must match extracted pages. Exact duplicates use SHA-256 over normalized body text. Near duplicates use cosine similarity between local document embeddings. Version 2.2 changes the near-duplicate quarantine threshold from 0.94 to 0.91; the new value applies to candidates in this revision and later revisions.

## Page 3

A pair at or above the active threshold is quarantined unless both records share a document identifier and are versions of the same source. The report includes the matching document id and measured similarity. A report must identify the verification-standard version used so an operator can distinguish historical outcomes calculated under the prior 0.94 threshold.
