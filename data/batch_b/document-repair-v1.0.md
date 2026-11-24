---
doc_id: document-repair
source: Aster Research Lab policy archive (fictional test corpus)
title: Document Repair Procedure
version: 1.0
date: 2026-11-12
page_count: 3
---

## Page 1

A quarantined source is repaired from a trusted original, not reconstructed from a generated answer. The curator compares its title, source, version, page count, and extracted pages with that original. A corrected source receives a new hash and an updated verification record. The original failed copy stays in quarantine for audit until the corrected version passes intake.

## Page 2

The operator reruns verification on the repaired document before it reaches chunking. Quality checks readable extraction, completeness checks required metadata and truncation, recency checks active revisions, and uniqueness checks exact and near copies. A single failed check is enough to keep the source out of the active collection.

## Page 3

Once the document passes, the ingestion writer replaces only that document's chunks and records the inserted and removed chunk counts. The query owner then runs a targeted question and checks the retrieved page and document version. If the repair changes an answer, the evaluation result records the change and the trace shows the supporting passage.
