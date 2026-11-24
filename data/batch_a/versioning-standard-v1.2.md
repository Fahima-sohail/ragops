---
doc_id: versioning-standard
source: Aster Research Lab policy archive (fictional test corpus)
title: Version and Archive Standard
version: 1.2
date: 2026-11-01
page_count: 3
---

## Page 1

A document identifier remains stable across revisions. Each revision has an explicit version string and a source hash. When a newer version arrives, the ingestion job copies the prior source file to the archive, marks its vector metadata as superseded, and indexes the new active version. Retrieval filters exclude superseded chunks by default. The archive keeps enough metadata to identify the former active version and the run that replaced it.

## Page 2

Version comparison uses numeric components when the version follows a dotted form such as 1.2 or 2.0. A release date is used when version strings cannot be compared. Two sources with unrelated document identifiers are never considered revisions merely because their titles are similar. An older revision arriving in an ordinary batch is archived as historical and does not replace a newer active revision.

## Page 3

A rollback names both the stable document id and the archived version to restore. The ingestion writer then marks the currently active chunks superseded, reactivates the requested archived version, and records the rollback event in its report. A rollback is a new auditable event; it does not erase the newer file or its trace history. The active version after rollback must be visible in a retrieval result and a query trace.
