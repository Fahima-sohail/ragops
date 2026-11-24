---
doc_id: versioning-standard
source: Aster Research Lab policy archive (fictional test corpus)
title: Version and Archive Standard
version: 1.3
date: 2026-11-10
page_count: 3
---

## Page 1

A document identifier remains stable across revisions. Each revision has an explicit version string and a source hash. When a newer version arrives, the ingestion job archives the prior source, marks its vectors superseded, and indexes the replacement as active. The active collection retains the prior vector rows for audit and rollback, but retrieval filters exclude superseded rows. Version 1.3 adds an operator confirmation step before a version is published.

## Page 2

Version comparison uses numeric components for dotted strings such as 1.2 and 2.0. A release date is consulted only when version strings cannot be compared. A file with the same document identifier and the same content hash is skipped. A new hash for a higher version replaces only the chunks for that document, and the ingestion report records the number of old and new chunks.

## Page 3

A rollback names the stable document id and archived version. The ingestion writer marks the active revision superseded and restores the selected archived source. The rollback event records who initiated the request, the previous active version, the restored version, and the reason. The new retrieval trace must show the restored version. The archived newer file remains available for a later corrected release.
