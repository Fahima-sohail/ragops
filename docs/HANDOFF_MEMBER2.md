# Member 2 handoff

This repository gives you the local RAG API, persistent Chroma schema, ingestion command, evaluation command, release gate, and trace writer. The `k8s/` directory is empty and reserved for your work. The local corpus is a fictional test set; it is not an official university policy corpus.

## Clone and install (Windows PowerShell)

```powershell
git clone https://github.com/Fahima-sohail/ragops.git
Set-Location ragops
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python scripts/build_sample_corpus.py
python scripts/download_models.py
```

`scripts/download_models.py` fills `data/model_cache/` and first checks for existing snapshots; cached models are never downloaded again. If a new clone has no cache and network access is available, run `python scripts/download_models.py --allow-download` once. Afterward keep `MODEL_CACHE_OFFLINE=1`. The cache is ignored by Git and is not part of the Docker build context. The Dockerfile runs `python scripts/download_models.py --allow-download` at image build time; an alternative deployment can mount a prefilled model cache at `/app/data/model_cache`. Ensure the API and evaluation Job see the same model files. No secret belongs in Git.

## Environment contract

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATA_DIR` | `data/batch_a` | Ingestion input directory or complete snapshot. |
| `QUARANTINE_DIR` | `data/quarantine` | Failed document copies and verification sidecars. |
| `ARCHIVE_DIR` | `data/archive` | Superseded source revisions and rollback input. |
| `TRACE_DIR` | `traces` | JSONL query traces. |
| `VECTOR_DIR` | `data/vector_store` | Persistent Chroma path; mount a PVC here. |
| `COLLECTION` | `ragops` | Chroma collection name. |
| `EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local query/document embedding model. |
| `LLM_API_KEY` | empty | Optional hosted model credential; keep it in a Kubernetes Secret. |
| `LLM_MODEL` | `Qwen/Qwen2.5-0.5B-Instruct` | Local Transformers model id or hosted API model name. |
| `TOP_K` | `5` | Maximum active chunks returned by retrieval. |
| `SIMILARITY_THRESHOLD` | `0.28` | Minimum top-1 cosine similarity required before generation. |
| `CHUNK_SIZE` | `220` | Whitespace-token chunk size. |
| `CHUNK_OVERLAP` | `40` | Chunk overlap in whitespace tokens. |
| `SEED` | `4032` | Evaluation seed. |

Additional local controls are `LLM_DEVICE` (defaults to CPU) and `NEAR_DUPLICATE_THRESHOLD` (defaults to `0.94`). The prompt temperature is fixed to zero.

## C1/C2 release candidates

The measured baseline and candidate collections are persistent Chroma collections under the same PVC. In each Deployment/Job, set the following exact environment values. Baseline and candidate versions must use the same `VECTOR_DIR`, corpus snapshot, embedding/model settings, chunk size/overlap, similarity threshold, and seed. C1 changes `TOP_K` from 3 to 8 and selects the corresponding collection. Keep the API volume mount read-only and give ingestion Jobs read-write access.

| Role | `COLLECTION` | `CHUNK_SIZE` | `CHUNK_OVERLAP` | `TOP_K` | `SIMILARITY_THRESHOLD` |
| --- | --- | ---: | ---: | ---: | ---: |
| Baseline after Batch B | `e3-before-b-500` | `500` | `50` | `3` | `0.28` |
| Passing candidate | `cand_topk8` | `500` | `50` | `8` | `0.28` |
| Deliberate failing candidate | `cand_topk1` | `500` | `50` | `1` | `0.99` |

Shared settings are `VECTOR_DIR=/app/data/vector_store`, `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`, `EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2`, `LLM_MODEL=Qwen/Qwen2.5-0.5B-Instruct`, `SEED=4032`, `TRACE_DIR=/app/traces`, `MODEL_CACHE_OFFLINE=1`, and `HF_HUB_OFFLINE=1`. Set `LLM_API_KEY` empty for the local model; if using a hosted LLM, supply it from a Kubernetes Secret. Set `DATA_DIR=/app/data/batch_a` for the first ingestion Job and `/app/data/batch_b` for the incremental Batch B Job. The corpus and chunk settings are identical in each collection; C1 changes only `COLLECTION` and `TOP_K`. The deliberate fail uses `TOP_K=1` and raises `SIMILARITY_THRESHOLD` to 0.99. Create each collection by running the Batch A and Batch B ingestion Jobs with the same chunk settings, then evaluate it.

The C2 TOP_K=3 baseline (`suite_20261126T155753Z.json`) measured faithfulness `1.0`, p95 latency `30,392.909 ms`, and recall@5 `0.958333`. The gate accepts faithfulness down to `0.95`, recall@5 loss up to `0.02`, citation validity at least `0.90`, abstention correctness no lower than baseline, and p95 up to `36,500 ms` (20% over measured baseline, rounded up). Thresholds can be mounted and selected without rebuilding the image by setting `GATE_CONFIG=/app/config/gate.yaml` on the gate Job.

Use these commands as the `command` / `args` inside Member 2's Kubernetes Jobs; put each role's environment table values in that Job's Pod spec:

```sh
python -m rag.ingest --data "$DATA_DIR" --collection "$COLLECTION"
python -m eval.run_suite --label "$CANDIDATE_LABEL" --no-gate
python -m eval.gate --candidate "$CANDIDATE_JSON" --baseline "$BASELINE_JSON"
```

The candidate suite Job must preserve its `suite_<timestamp>.json` output and copy the metric payload to the candidate JSON path used by the gate Job. The gate Job mounts the baseline JSON, candidate JSON, and `$GATE_CONFIG` read-only and propagates the command's exit code. `C2_gate_pass.txt`, `C2_gate_fail.txt`, and `C_release_decision.md` show the recorded local outcomes. Kubernetes rollout and rollback manifests remain Member 2 work under `k8s/`.

## Commands and ownership

Member 1 commands:

```powershell
python -m rag.ingest --data $env:DATA_DIR --collection $env:COLLECTION
python -m eval.run_suite
python -m eval.gate --candidate eval/results/candidate.json --baseline eval/results/baseline.json --config gate.yaml
uvicorn rag.api:app --port 8000
```

The API exposes `POST /query`, `GET /health`, and `GET /metrics`. It opens Chroma read-only. `rag.ingest` is the only vector-store writer. Verification reports and suite results are saved to `eval/results/`; query traces are saved to `traces/`.

Member 2 implementation:

- Own all manifests under `k8s/`, including Deployment/Service, persistent volumes, ingestion and evaluation Jobs, CronJob, ConfigMap, controlled candidate rollout, rollback, and resource measurements.
- Add `k8s/README.md` with exact cluster setup/apply/Job/rollout commands.
- Add the live-query log and coverage/drift commands for Part E.
- Add the metrics-window summary script and trace-id inspection tool. The trace tool should print the exact prompt and retrieved context without modifying the trace.
- Capture only real cluster output and screenshots; do not create reports from imagined Pods or measurements.

## Trace schema

Each JSON line contains: `trace_id`, `timestamp`, `user_query`, `rewritten_query`, `embedding_model`, `embedding_version`, `collection`, `retrieved` entries with `chunk_id`, `doc_id`, `doc_version`, `score`, `title`, and `page`, `filters`, `reranked_order`, `prompt_hash`, `prompt`, `model`, `params`, `response`, `citations`, `guardrail_actions`, `latency_ms` (`embed`, `retrieve`, `rerank`, `generate`, `total`), and `cache_hit`.

`rag.trace` appends each real query to `$TRACE_DIR/traces.jsonl` and prints the same JSON line to stdout. `traces/example.jsonl` is a committed real example; Member 2's trace tool should accept the trace id and display the prompt plus the exact text represented by retrieved chunk ids.

## Kubernetes contract

- Mount `VECTOR_DIR` persistently; the API mount must be read-only and the ingestion Job mount read-write.
- Mount the data lake, quarantine, archive, traces, and results on persistent storage.
- The API runs from `rag.api:app`; route paths are `/query`, `/health`, and `/metrics`.
- The evaluation Job runs `python -m eval.run_suite` and propagates its exit code.
- Gate thresholds are read from `gate.yaml`; changing them must not require rebuilding the API image.
- Candidate collection and embedding identity must be visible in a trace after release and after rollback.
