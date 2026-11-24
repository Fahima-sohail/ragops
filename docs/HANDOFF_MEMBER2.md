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
| `CHUNK_SIZE` | `220` | Whitespace-token chunk size. |
| `CHUNK_OVERLAP` | `40` | Chunk overlap in whitespace tokens. |
| `SEED` | `4032` | Evaluation seed. |

Additional local controls are `LLM_DEVICE` (defaults to CPU) and `NEAR_DUPLICATE_THRESHOLD` (defaults to `0.94`). The prompt temperature is fixed to zero.

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

`traces/example.jsonl` is populated by the first real query. Member 2's trace tool should accept the trace id and display the prompt plus the exact text represented by retrieved chunk ids.

## Kubernetes contract

- Mount `VECTOR_DIR` persistently; the API mount must be read-only and the ingestion Job mount read-write.
- Mount the data lake, quarantine, archive, traces, and results on persistent storage.
- The API runs from `rag.api:app`; route paths are `/query`, `/health`, and `/metrics`.
- The evaluation Job runs `python -m eval.run_suite` and propagates its exit code.
- Gate thresholds are read from `gate.yaml`; changing them must not require rebuilding the API image.
- Candidate collection and embedding identity must be visible in a trace after release and after rollback.
