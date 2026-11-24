# RAGOps: CS4032 Assignment 03

This repository contains a local, persistent RAG pipeline and the Member 1 implementation for data verification, evaluation, gating, tracing, and the read-only query API. The bundled Aster Research Lab documents are a fictional test corpus, not university policy. See [Assignment_03.pdf](docs/Assignment_03.pdf), [DECISIONS.md](docs/DECISIONS.md), and [HANDOFF_MEMBER2.md](docs/HANDOFF_MEMBER2.md).

## Local setup (Windows PowerShell)

Python 3.11 or newer is required. The repository was run with Python 3.13.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python scripts/build_sample_corpus.py
python scripts/download_models.py
```

`scripts/download_models.py` checks the ignored `data/model_cache/` first and skips any model already present. On a fresh clone without cached models, run `python scripts/download_models.py --allow-download` once while connected, then keep `MODEL_CACHE_OFFLINE=1` for operation. With no `LLM_API_KEY`, generation uses the local Transformers model. Temperature is fixed at zero.

Set defaults for the shell, or edit `.env`:

```powershell
$env:DATA_DIR = 'data/batch_a'
$env:QUARANTINE_DIR = 'data/quarantine'
$env:ARCHIVE_DIR = 'data/archive'
$env:TRACE_DIR = 'traces'
$env:VECTOR_DIR = 'data/vector_store'
$env:COLLECTION = 'ragops'
$env:EMBED_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
$env:LLM_MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'
$env:TOP_K = '5'
$env:CHUNK_SIZE = '220'
$env:CHUNK_OVERLAP = '40'
$env:SEED = '4032'
```

## Part A - Data management

Create the local sample documents, ingest Batch A, and rerun the same command to demonstrate zero new chunk embeddings for unchanged sources:

```powershell
python scripts/build_sample_corpus.py
python -m rag.ingest --data $env:DATA_DIR --collection $env:COLLECTION
python -m rag.ingest --data $env:DATA_DIR --collection $env:COLLECTION
```

To preserve initial-ingestion evidence without resetting the active collection, use a separate collection for the demonstration:

```powershell
python -m rag.ingest --data data/batch_a --collection ragops_initial_demo
python -m rag.ingest --data data/batch_a --collection ragops_initial_demo
```

Ingest Batch B as an incremental batch. Verification failures are moved to `data/quarantine/<run-id>/`; the newer `versioning-standard` revision is archived and the active Chroma metadata is updated. The verification report is written to `eval/results/verification_<run-id>.json`.

```powershell
python -m rag.ingest --data data/batch_b --collection $env:COLLECTION
python -m rag.ingest --data data --collection $env:COLLECTION
```

Use `--sync` only when the selected directory is a complete corpus snapshot; it deletes indexed document ids missing from that snapshot. To show a deletion without disturbing the main collection, use a separate collection:

```powershell
New-Item -ItemType Directory -Force tmp\delete-demo | Out-Null
Copy-Item data/batch_a/service-charter-v1.0.md tmp\delete-demo\
python -m rag.ingest --data tmp\delete-demo --collection delete-demo --sync
Remove-Item tmp\delete-demo\service-charter-v1.0.md
python -m rag.ingest --data tmp\delete-demo --collection delete-demo --sync
```

The second verification result records the deleted chunk count by document id. To restore an archived version after Batch B:

```powershell
python -m rag.ingest --restore versioning-standard --version 1.2 --collection $env:COLLECTION
```

## Part B - Offline evaluation

`eval/golden.jsonl` has 25 proposed questions: 20 answerable, five unanswerable, and five hard. Eight human-authorship proposals and eight proposed synthetic reviews are marked pending in `eval/review/golden_questions.md`. Do not report those labels as approved until the user reviews the file and replies `approved`.

```powershell
python -m eval.run_suite
```

The suite computes embedding similarity, determinism, recall@3/5, MRR, nDCG@5, a three-document noise check, answer grounding, abstention correctness, citation validity, latency, and two seeded runs. It writes timestamped results under `eval/results/`. Results remain provisional while human review is pending. The command exits with status 1 if the configured release gate fails.

## Part C - Change experiment and release gate

The baseline is `TOP_K=5`; the passing candidate experiment raises it to six and compares the same corpus and questions.

```powershell
python -m eval.run_suite --candidate-top-k 6
python -m eval.gate --candidate eval/results/candidate.json --baseline eval/results/baseline.json --config gate.yaml
```

The deliberately bad `TOP_K=1` candidate is expected to fail when it loses more than two percentage points of recall@5. Restore the passing candidate result after recording the failure:

```powershell
python -m eval.run_suite --candidate-top-k 1
python -m eval.gate --candidate eval/results/candidate.json --baseline eval/results/baseline.json --config gate.yaml
python -m eval.run_suite --candidate-top-k 6
```

Thresholds and their local CPU rationale are in `gate.yaml`. Kubernetes rollout and rollback evidence belongs to Member 2.

## Part D - Observability and tracing

Start the API after ingestion. The API is read-only against Chroma; only `rag.ingest` writes vectors.

```powershell
uvicorn rag.api:app --port 8000
```

In another PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/query -ContentType 'application/json' -Body '{"query":"Which component is allowed to write to the vector store?"}'
Invoke-RestMethod http://127.0.0.1:8000/metrics
```

Every query is appended to `traces/queries_YYYYMMDD.jsonl`; the first real query also creates `traces/example.jsonl`. The trace writer includes the exact prompt, retrieved ids and versions, citations, guardrail actions, cache state, and stage latencies. Member 2 fills the trace inspection command.

## Part E - Live-query coverage and drift

Member 2 fills the live-query set, coverage script, metrics summary script, and trace inspection tool. The expected workflow is: add at least 40 live queries, compare each with the closest golden question, list uncovered topics, run Batch B evaluation, add six approved coverage questions, then rerun the gate. No live-user logs or coverage percentages are fabricated in this repository.

## Part F - Kubernetes

The demo must run on Kubernetes; running only Docker containers receives zero. `k8s/` is reserved for Member 2 and was not edited by Member 1. Member 2 fills `k8s/README.md` with the apply, Job, rollout, rollback, PVC, and port-forward commands. The local API Dockerfile is provided for building an image, not as a substitute for the Kubernetes demo.

## Part G - Report evidence

Use only real results from `eval/results/` and real JSONL records under `traces/`. Report the pending-review status explicitly until approval is recorded. Kubernetes measurements and screenshots are supplied by Member 2 after a real cluster run. See `report/README.md` for the evidence map.
