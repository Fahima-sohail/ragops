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

`eval/golden.jsonl` contains 43 questions: 27 answerable, seven unanswerable, and nine hard. It has 33 synthetic questions and ten entries with `source="human"`, filled and merged from `eval/human_questions_todo.md`. The user confirmed reviewing all ten human-source entries; those and exactly ten synthetic rows have `reviewed=true`. All 43 ground-truth references were checked against active indexed document pages. The loader tolerates unfilled placeholders and avoids double-counting completed rows already merged into the golden set.

```powershell
$env:COLLECTION = "a-demo-20261125-012139"
$env:SEED = "4032"
$env:MODEL_CACHE_OFFLINE = "1"
$env:HF_HUB_OFFLINE = "1"
$env:LLM_API_KEY = ""
python -m eval.validate_golden
python -m eval.run_suite --label member1-end-to-end
python -m eval.gate --candidate eval/results/candidate.json --baseline eval/results/baseline.json --config gate.yaml
python -m eval.stochasticity
```

`eval.run_suite` runs the module, component, and end-to-end levels, writes a timestamped JSON result and Markdown summary, prints the metric and gate tables, then applies `gate.yaml` against `eval/results/baseline.json`. The first real suite run creates that baseline. It supports `--label TEXT` and `--no-gate`; `COLLECTION` selects the indexed Chroma collection. The embedding module reports paraphrase/unrelated cosine, gap, time per chunk, and repeat-embedding determinism. Retrieval reports doc/page recall@3/5, MRR, and nDCG@5 for clean, typo, and noise conditions; noise records exist only in a temporary in-memory collection. End-to-end evaluation runs each golden question through the actual query pipeline, uses temperature zero for the generation and LLM grounding judge, and reports faithfulness, abstention and false-abstention rates, citation validity, and query latency p50/p95. `eval.stochasticity` repeats the suite twice with the configured seed and records metric differences plus explanations for any nonzero difference. All result-producing commands use the cached local models with `MODEL_CACHE_OFFLINE=1` and `HF_HUB_OFFLINE=1`.

`eval/e2e.py` writes ten real answer/context/judge-score samples to `eval/judge_labels.csv`; after the user authorized manual labeling, all ten sampled claims were checked against their quoted contexts and labeled `supported`. Their matching real query traces are committed in `traces/e2e_sample_run.jsonl`, and agreement is recorded in `eval/results/judge_agreement_20261126T162229Z.json`. A canonical abstention has no factual claims and receives faithfulness 1 by vacuous truth; the report counts these separately from calls to the local LLM judge. The suite exits 1 if a configured release-gate check fails.

## Part C - Change experiment and release gate

The C1 experiment changes only `TOP_K` through environment variables: baseline 3 versus candidate 8, using separate Chroma collections with identical Batch A + Batch B documents and identical Chunk Size 500 / Overlap 50 settings. The corpus pages are each below 250 words, so changing chunk size from 500 to 250 would create no new chunks. The deliberate C2 failure uses `TOP_K=1` and `SIMILARITY_THRESHOLD=0.99`. All three levels are measured by `eval.run_suite`; the results and deltas are recorded in `eval/results/C1_comparison.md`.

For E3, the same 43-question set runs against Batch A and then after staged Batch B ingestion. `EVAL_ALLOW_MISSING_GROUND_TRUTH=1` records Batch-B-only pages missing from the before corpus; `EVAL_ALLOW_GROUND_TRUTH_DRIFT=1` records reference answers changed by the newer active version in the after corpus. Both flags leave page-level retrieval metrics intact and are off for normal release validation.

```powershell
$env:COLLECTION = "e3-before-b-500"
$env:CHUNK_SIZE = "500"
$env:CHUNK_OVERLAP = "50"
$env:TOP_K = "3"
python -m eval.run_suite --label C1-baseline-topk3 --no-gate
$env:COLLECTION = "cand_topk8"
$env:TOP_K = "8"
python -m eval.run_suite --label C1-candidate-topk8 --no-gate
python -m eval.gate --candidate eval/results/C2_candidate_pass.json --baseline eval/results/C2_baseline.json
python -m eval.gate --candidate eval/results/C2_candidate_fail.json --baseline eval/results/C2_baseline.json
```

`eval.gate` supports `GATE_CONFIG` for a mounted threshold file; explicit `--config` takes precedence. The C2 TOP_K=3 baseline measured faithfulness 1.0 and p95 latency 30,392.909 ms. `gate.yaml` therefore uses faithfulness >=0.95 and p95 <=36,500 ms (20% over the measured p95, rounded up), with a 0.02 maximum recall@5 drop, citation validity >=0.90, and no abstention-correctness regression. The rationale and actual gate outputs are committed alongside `C_release_decision.md`. Kubernetes rollout and rollback evidence belongs to Member 2.

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
