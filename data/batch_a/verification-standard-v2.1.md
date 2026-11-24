---
doc_id: verification-standard
source: Aster Research Lab policy archive (fictional test corpus)
title: Document Verification Standard
version: 2.1
date: 2026-11-01
page_count: 3
---

## Page 1

Quality verification rejects empty text, garbled extraction, or an extraction failure. The checker requires a minimum amount of readable text and rejects a document when replacement characters or non-printing characters dominate. A text file ending halfway through a word or sentence is incomplete when the manifest also marks it truncated. The verifier records pass or fail separately for quality, completeness, recency, and uniqueness, together with a concise reason for each result.

## Page 2

Completeness verification requires source, title, a date or version, and page count. The declared page count must match extracted pages. Text that contains only a title, a single navigation label, or an explicit truncation marker does not pass. A PDF extraction error is recorded as a quality failure rather than silently converted into an empty indexed record. A missing metadata field is a completeness failure even if the text itself is readable.

## Page 3

Exact duplicates are detected with SHA-256 over normalized extracted body text. Near duplicates are detected with cosine similarity between local document embeddings. The test threshold is 0.94; a pair at or above that value is quarantined unless both records share a document identifier and are versions of the same source. The report includes the matching document id and the measured similarity so an operator can explain the decision.
