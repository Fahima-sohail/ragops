---
doc_id: intake-copy-one
source: Aster Research Lab policy archive (fictional test corpus)
title: Document Intake Standard
version: 1.4
date: 2026-11-02
page_count: 3
---

## Page 1

An intake batch is a dated set of source files supplied to the Aster Research Lab assistant. Accepted formats are UTF-8 Markdown, UTF-8 text, and searchable PDF. Each file carries a stable document identifier, a title, a date or version, a source description, and a page count. The manifest records the SHA-256 hash of the extracted body, the original filename, and the batch label. The batch operator preserves original source files until verification finishes.

## Page 2

The intake job reads files in stable path order and never follows symbolic links outside the selected data directory. It ignores the archive, quarantine, and vector-store directories. A new batch is verified before chunking. A file that fails verification is moved to quarantine with its report record; passing files proceed to the chunker. Operators compare the batch manifest with the last successful run before they publish a collection.

## Page 3

A repeated intake of unchanged sources must create no new chunk embeddings. A changed source replaces only the chunks belonging to that document. A full snapshot run removes chunks for a document that has been deleted from that snapshot. Incremental batch imports leave unrelated documents in place. The result file records discovered files, verified files, quarantined files, inserted chunks, replaced chunks, skipped chunks, and deleted chunks.
