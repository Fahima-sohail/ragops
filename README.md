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
$env:SIMILARITY_THRESHOLD = '0.28'
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
Each collection also has a `<collection>.manifest.json` next to Chroma, recording each document id, content hash, version, active or archived status, and chunk ids. Repeated unchanged runs report zero embedded chunks. Use `--count-by-doc` to inspect stored counts, including an explicit zero for a requested id.

```powershell
New-Item -ItemType Directory -Force tmp\batch-b-run | Out-Null
Copy-Item data\batch_b\* tmp\batch-b-run -Force
python -m rag.ingest --data tmp\batch-b-run --collection $env:COLLECTION
New-Item -ItemType Directory -Force tmp\combined-run | Out-Null
Copy-Item data\batch_a\* tmp\combined-run -Force
Copy-Item data\batch_b\* tmp\combined-run -Force
python -m rag.ingest --data tmp\combined-run --collection $env:COLLECTION
```

Use `--sync` only when the selected directory is a complete corpus snapshot; it deletes indexed document ids missing from that snapshot. To show a deletion without disturbing the main collection, use a separate collection:

```powershell
New-Item -ItemType Directory -Force tmp\delete-initial | Out-Null
Copy-Item data\batch_a\service-charter-v1.0.md -Destination tmp\delete-initial -Force
Copy-Item data\batch_a\storage-backup-v1.1.md -Destination tmp\delete-initial -Force
python -m rag.ingest --data tmp\delete-initial --collection a2-delete-demo --sync
New-Item -ItemType Directory -Force tmp\delete-remaining | Out-Null
Copy-Item data\batch_a\service-charter-v1.0.md -Destination tmp\delete-remaining -Force
python -m rag.ingest --data tmp\delete-remaining --collection a2-delete-demo --sync
```

The second verification result records the deleted chunk count by document id. To demonstrate a same-version document replacement while preserving unrelated chunks:

```powershell
New-Item -ItemType Directory -Force tmp\change-initial | Out-Null
Copy-Item data\batch_a\service-charter-v1.0.md -Destination tmp\change-initial -Force
Copy-Item data\batch_a\storage-backup-v1.1.md -Destination tmp\change-initial -Force
python -m rag.ingest --data tmp\change-initial --collection a2-change-demo --sync
New-Item -ItemType Directory -Force tmp\change-revised | Out-Null
Copy-Item data\batch_a\service-charter-v1.0.md -Destination tmp\change-revised -Force
Copy-Item data\batch_a\storage-backup-v1.1.md -Destination tmp\change-revised -Force
Add-Content tmp\change-revised\service-charter-v1.0.md 'A2 change fixture: owner records this replacement for the targeted source only.'
python -m rag.ingest --data tmp\change-revised --collection a2-change-demo --sync
```

To restore an archived version after Batch B:

```powershell
python -m rag.ingest --count-by-doc --collection $env:COLLECTION
python -m rag.ingest --count-by-doc --collection $env:COLLECTION --doc-id source-provenance
python -m rag.ingest --restore verification-standard 2.1 --collection $env:COLLECTION
```

For the complete, repeatable Part A sequence with real console output captured at `eval/results/A_demo_log.txt`, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_a_demo.ps1
```

`SCREENSHOTS.md` lists the individual commands in screenshot order.

## Part B - Offline evaluation

`eval/golden.jsonl` uses the Part B schema and currently contains 33 synthetic questions: 21 answerable, six unanswerable, and six hard. Exactly ten synthetic questions have `reviewed=true`; their source pages are checked by `eval.validate_golden` against active indexed text. Ten human-authored placeholders are kept separately in `eval/human_questions_todo.md`. The loader skips untouched placeholders and includes completed entries after their fields and source pages are filled.

```powershell
python -m eval.generate_questions --max-new-tokens 220
python -m eval.validate_golden
python -m eval.module_embedding
python -m eval.component_retrieval
python -m eval.run_suite
```

Question generation uses the cached local LLM in offline mode and writes the raw prompt/output to `eval/results/`. The validation command checks every answer reference against the selected active collection. The embedding module reports the mean cosine for 15+ paraphrase and unrelated pairs, their gap, time per active chunk, and repeat-embedding determinism. The retrieval component reports doc/page-level recall@3/5, MRR, and nDCG@5 for clean, typo-query, and noise-document conditions; it copies the corpus into a temporary in-memory Chroma collection, adds three noise documents there, and verifies the main collection count is unchanged. Each script records the configured `SEED` and writes a result under `eval/results/`.

The end-to-end suite computes answer grounding, abstention correctness, citation validity, latency, and two seeded runs. It writes timestamped results under `eval/results/`. Results remain provisional until at least eight human questions are supplied and reviewed. The command exits with status 1 if the configured release gate fails.

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
New-Item -ItemType Directory -Force tmp | Out-Null
Set-Content -LiteralPath tmp\api-query.json -Value '{"question":"Which component is allowed to write to the vector store?"}' -Encoding Ascii -NoNewline
curl.exe -sS -X POST http://127.0.0.1:8000/query -H "Content-Type: application/json" --data-binary "@tmp\api-query.json"
curl.exe -sS http://127.0.0.1:8000/metrics
```

Every query is appended as one JSON line to `$TRACE_DIR/traces.jsonl` and the same line is printed to stdout. Traces include the full prompt and its SHA-256 hash, retrieved chunk ids, citations, structured guardrail actions, cache state, and latency for each stage. The API abstains with `I don't know based on the documents` when similarity is below `SIMILARITY_THRESHOLD` (default `0.28`) or the safe context does not support the question. `/metrics` returns Prometheus text with request counters and latency / similarity histograms. Member 2 fills the trace inspection command.

## Part E - Live-query coverage and drift

Member 2 fills the live-query set, coverage script, metrics summary script, and trace inspection tool. The expected workflow is: add at least 40 live queries, compare each with the closest golden question, list uncovered topics, run Batch B evaluation, add six approved coverage questions, then rerun the gate. No live-user logs or coverage percentages are fabricated in this repository.

## Part F - Kubernetes

The demo must run on Kubernetes; running only Docker containers receives zero. `k8s/` is reserved for Member 2 and was not edited by Member 1. Member 2 fills `k8s/README.md` with the apply, Job, rollout, rollback, PVC, and port-forward commands. The local API Dockerfile is provided for building an image, not as a substitute for the Kubernetes demo.

## Part G - Report evidence

Use only real results from `eval/results/` and real JSONL records under `traces/`. Report the pending-review status explicitly until approval is recorded. Kubernetes measurements and screenshots are supplied by Member 2 after a real cluster run. See `report/README.md` for the evidence map.
