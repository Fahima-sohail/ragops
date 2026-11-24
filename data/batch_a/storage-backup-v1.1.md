---
doc_id: storage-backup
source: Aster Research Lab policy archive (fictional test corpus)
title: Persistent Storage and Backup Standard
version: 1.1
date: 2026-11-01
page_count: 3
---

## Page 1

The vector collection uses a persistent Chroma directory so it can be mounted from a persistent volume. The data lake, quarantine directory, archived revisions, traces, and evaluation results also need durable storage. The API mounts the vector directory read-only. The ingestion job mounts it read-write and owns all collection updates. Local development uses the same path contract through VECTOR_DIR.

## Page 2

A backup captures the Chroma data directory and the source manifest at a consistent point after ingestion completes. Operators record the backup timestamp, collection name, active document versions, and verification report. Restoring a backup is followed by a document-count comparison and a query against a known answer. The backup is not considered valid until the restored collection can be queried with the configured embedding model.

## Page 3

Temporary work files are written outside the active collection and removed after a successful run. Quarantined sources are retained with their reasons so a curator can repair them. Archived revisions are immutable except when copied for an explicit restore. Evaluation results and trace samples are committed to the repository only after their content has been checked for keys and other secrets.
