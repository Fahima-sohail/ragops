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
- Next: test A2 unchanged ingestion, changed-document replacement, deletion/sync, and archive rollback. Keep all model access offline.
