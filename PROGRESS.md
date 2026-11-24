# Progress

## 2026-11-24

- Initialized this repository on `main` and configured the empty GitHub repository `Fahima-sohail/ragops` as `origin`.
- Copied the complete Assignment 03 PDF to `docs/Assignment_03.pdf` and extracted all five pages to `docs/assignment_03_extracted.txt` for searchable local reference.
- Following the user's latest direction, implementation and data will be created only inside this repository. No RAHBAR starter files are being changed or copied.
- Current step: build the self-contained RAGOps implementation and locally authored, clearly fictional sample corpus. Human-review labels remain drafts pending the user's `approved` reply.

## 2026-11-25

- Read `AGENTS.md`, `PROGRESS.md`, and Git history before continuing. `main` and `origin/main` are synchronized at `6db81b0`; there were no unpushed commits or local edits.
- Confirmed both local model snapshots already exist under ignored `data/model_cache/`. Keep `MODEL_CACHE_OFFLINE=1`; do not download them again.
- Added `scripts/download_models.py`. It checks the local cache first and only downloads missing snapshots when explicitly passed `--allow-download`.
- Updated Member 2 handoff and Docker build behavior: Docker runs the model download/check script at build time, or a prefilled cache may be mounted at `/app/data/model_cache`.
- Pushed that step as `77a9c91 Add model cache handoff and downloader`. The cache test ran with `HF_HUB_OFFLINE=1`; both model snapshots were reported already cached and `pip check` passed.

### Part A1 verification

- Fixed within-batch recency selection so older versions in one batch fail, and keyed near-duplicate vectors by input record rather than a potentially shared document id.
- Avoided changing Chroma's immutable HNSW distance setting when recording index generations; ingestion now writes the generation marker under the persistent vector directory for the read-only API to read.
- Added two Batch B records and `data/batch_b/PLANTED.md`; Batch B now has 13 source fixtures. The manifest is excluded from document discovery.
- `python -m pytest -q`: **12 passed**.
- Real Batch B verification on the existing 36-chunk Batch A collection `ragops_initial_demo`: 13 discovered, 7 passed, 6 quarantined, 21 new chunks embedded. The report is `eval/results/verification_20261124T194200Z-250100.json`.
- The report identifies two exact duplicates, one near duplicate (cosine 0.9982), one corrupt extraction, one missing-metadata record, and one truncated record. It archived version 1.2 of `versioning-standard`; Chroma shows 3 old chunks superseded and 3 version 1.3 chunks active.
- An earlier local trial exposed Chroma's immutable-distance metadata behavior after vector changes. That unreported trial is not evidence; the A1 result above used the clean pre-existing Batch A collection and the corrected generation marker.

### Part A2 incremental update

- A second real Batch B run (`verification_20261124T194825Z-572500.json`) discovered 13 documents, passed the same 7, quarantined the same 6, embedded **0** chunks, and skipped **21** unchanged chunks with per-document counts.
- Changed-document demo (`verification_20261124T195101Z-299500.json`): `service-charter` replaced 3 chunks and embedded 3; unrelated `storage-backup` kept its 3 existing chunks and embedded 0.
- Deletion/sync demo (`verification_20261124T195240Z-941100.json`): removed **3** orphan chunks for document id `storage-backup`; the collection retained 3 `service-charter` chunks and 0 `storage-backup` chunks.
- Rollback demo (`verification_20261124T195336Z-403600.json`): restored archived `versioning-standard` v1.2 by reactivating 3 stored chunks and embedding 0. The trace-free read-only retriever returned v1.2 on pages 1 and 3, and Chroma metadata shows v1.2 active (3 chunks) and v1.3 superseded (3 chunks).
- Added by-document counts to ingestion reports and a regression test for scoped replacement/idempotency. `python -m pytest -q`: **13 passed**.
- Model cache remained offline throughout these runs; no model files were downloaded.

### Part A2 manifest, status filtering, and combined demo

- Added a per-collection JSON manifest beside the Chroma database. It records document id, content hash, version, active/archived status, and sorted chunk ids; ingestion refreshes it after indexing, sync deletion, and rollback.
- Chunk metadata now uses `status=active` or `status=archived`; retrieval filters to active chunks. The CLI accepts `python -m rag.ingest --restore DOC_ID VERSION` and `--count-by-doc`, including `--doc-id ID` to show a zero count after deletion.
- Added Batch B `verification-standard` v2.2, which changes the near-duplicate threshold fact from Batch A v2.1's 0.94 to 0.91. Batch B now has 14 source files; `PLANTED.md` lists each planted fixture and the changed fact.
- The complete real run is recorded in `eval/results/A_demo_log.txt`. Collection `a-demo-20261125-012139` indexed Batch A's 12 documents / 36 chunks, then reported 12 unchanged documents, 36 unchanged chunks, and 0 embedded chunks on rerun.
- Batch B reported 6 new documents, 2 updated documents, 24 embedded chunks, and 6 quarantined documents. The full-snapshot sync removed 3 chunks for the deleted `source-provenance` document; `--count-by-doc --doc-id source-provenance` printed `source-provenance: 0`.
- The demo restored archived `verification-standard` v2.1 with 3 reactivated chunks and 0 embedded chunks. A real read-only retrieval returned v2.2 / 0.91 before rollback and v2.1 / 0.94 afterward. The CLI also records a v1.2 restore of `versioning-standard`.
- `SCREENSHOTS.md` gives the Part A commands in order; `scripts/run_a_demo.ps1` repeats the end-to-end sequence and writes its real console output under `eval/results/` with model cache offline.
- With `MODEL_CACHE_OFFLINE=1` and `HF_HUB_OFFLINE=1`, `python -m pytest -q` passed: **15 passed**.

### Part D1/D4 API, tracing, and retrieval guardrail

- `rag.trace` now validates the exact 19-field AGENTS schema, appends one line per query to `$TRACE_DIR/traces.jsonl`, and prints the identical serialized line to stdout. Cache hits get a fresh trace id and zero per-stage work latency.
- Added structured injection rules/actions (`rule_name`, `chunk_id`, `doc_id`, `action_taken`); matching retrieved chunks are removed before prompt construction. The `SIMILARITY_THRESHOLD` default is 0.28, and unsupported or low-similarity questions return exactly `I don't know based on the documents`.
- The API accepts `POST /query` with `question` (and retains `query` as an input alias), exposes `/health`, and returns Prometheus counters plus per-stage latency and top-1 similarity histograms from `/metrics`. API retrieval uses the read-only Chroma path.
- `tests/test_api_tracing.py` covers exact trace fields/stdout, injection removal, prompt exclusion, cache behavior, abstention, aliases, and metric output. Offline `python -m pytest -q`: **21 passed**.
- Ingested the Batch B injection record into `a-demo-20261125-012139` (unchanged: 1 document, 0 embedded chunks), then ran the local API and three real curl requests. The first retrieved `injection-test-record`; three matching rules removed its malicious chunk, and that chunk is absent from the full prompt. The second grounded query cited the storage standard; the repeated query returned `cache_hit=true`.
- The live API reported `queries_total=3`, `cache_hits_total=1`, `injections_flagged_total=1` (one distinct chunk), and `abstentions_total=0`. Health, Prometheus output, and the real response payloads are committed in `eval/results/D1D4_api_run.txt`.
- Copied the three validated live records to `traces/sample_run.jsonl` and the D4 record to `traces/example.jsonl`. D4 trace id is `0c79c5fd-9bda-4726-b00b-f1c89a7dfb98`; it has three structured guardrail actions. No model downloads were attempted.
