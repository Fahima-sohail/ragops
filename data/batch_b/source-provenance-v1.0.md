---
doc_id: source-provenance
source: Aster Research Lab policy archive (fictional test corpus)
title: Source Provenance Register
version: 1.0
date: 2026-11-12
page_count: 3
---

## Page 1

Every source entry records a stable document id, source location, title, version or publication date, page count, and content hash. A provenance entry describes whether the file was supplied as a fixture, exported from an approved archive, or copied from an original PDF. The sample Aster Research Lab records in this repository are fictional test content and are not official institutional policies.

## Page 2

The manifest stores the original filename and the intake batch identifier. It records the extraction parser and the embedding model version used for the index run. A document with uncertain authorship or missing source context fails completeness rather than being promoted as an authoritative policy.

## Page 3

When a source is replaced, the manifest links the new version to the previous version and the verification report for that run. Archived versions keep their original hashes. Restoring an older version adds a rollback event without deleting the newer provenance record.
