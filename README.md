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

### Commands and expected outputs

| Command | Expected output artifact |
| --- | --- |
| `python -m rag.ingest --data $env:DATA_DIR --collection $env:COLLECTION` | `eval/results/verification_<run-id>.json` and `data/vector_store/<collection>.manifest.json` |
| Run the same ingestion command again on unchanged Batch A | A second verification JSON with `embedded_chunks: 0`; full console sequence: `eval/results/A_demo_log.txt` |
| `$env:DATA_DIR = 'data/batch_b'` then `python -m rag.ingest --data $env:DATA_DIR --collection $env:COLLECTION` | A verification JSON with the four check outcomes, quarantine decisions, and archive versions |
| `python -m rag.ingest --count-by-doc --collection $env:COLLECTION --doc-id source-provenance` | Per-document counts on stdout; the deletion proof (`source-provenance: 0`) is recorded in `eval/results/A_demo_log.txt` |
| `python -m rag.ingest --restore verification-standard 2.1 --collection $env:COLLECTION` | Restore verification JSON; recorded rollback output is in `eval/results/A_demo_log.txt` |

Run the complete sequence, including unchanged ingestion, Batch B, deletion, and restore, with:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_a_demo.ps1
```

Expected captured output: [`eval/results/A_demo_log.txt`](eval/results/A_demo_log.txt). Individual run reports use `eval/results/verification_<run-id>.json`.

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

### Commands and expected outputs

| Command | Expected output artifact |
| --- | --- |
| `python -m eval.validate_golden` | `eval/results/golden_validation_<timestamp>.json` |
| `python -m eval.module_embedding` | `eval/results/embedding_<timestamp>.json` |
| `python -m eval.component_retrieval` | `eval/results/retrieval_component_<timestamp>.json` |
| `python -m eval.e2e` | `eval/results/e2e_<timestamp>.json` and `eval/judge_labels.csv` |
| `python -m eval.judge_agreement` | `eval/results/judge_agreement_<timestamp>.json` |
| `python -m eval.stochasticity` | `eval/results/stochasticity_<timestamp>.json` |
| `python -m eval.run_suite --label member1-end-to-end` | `eval/results/suite_<timestamp>.json`, `suite_<timestamp>.md`, plus `baseline.json` on the first run and `candidate.json` |

The committed three-level example is [`eval/results/suite_20261126T155753Z.json`](eval/results/suite_20261126T155753Z.json) with its Markdown summary beside it. Keep `MODEL_CACHE_OFFLINE=1` and `HF_HUB_OFFLINE=1` for local runs.

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

### Commands and expected outputs

Use the same corpus and model settings for both collections; only `TOP_K` and `COLLECTION` change:

```powershell
$env:COLLECTION = "e3-before-b-500"
$env:TOP_K = "3"
python -m eval.run_suite --label C1-baseline-topk3 --no-gate
$env:COLLECTION = "cand_topk8"
$env:TOP_K = "8"
$env:SIMILARITY_THRESHOLD = "0.28"
python -m eval.run_suite --label C1-candidate-topk8 --no-gate
Copy-Item eval/results/candidate.json eval/results/C2_candidate_pass.json -Force
$env:COLLECTION = "cand_topk1"
$env:TOP_K = "1"
$env:SIMILARITY_THRESHOLD = "0.99"
python -m eval.run_suite --label C2-deliberate-fail-topk1 --no-gate
Copy-Item eval/results/candidate.json eval/results/C2_candidate_fail.json -Force
python -m eval.gate --candidate eval/results/C2_candidate_pass.json --baseline eval/results/C2_baseline.json --config gate.yaml
python -m eval.gate --candidate eval/results/C2_candidate_fail.json --baseline eval/results/C2_baseline.json --config gate.yaml
```

Expected outputs: `eval/results/suite_<timestamp>.json` and `.md` for both runs; `eval/results/C1_comparison.md`; `eval/results/C2_gate_pass.txt`; `eval/results/C2_gate_fail.txt`; and `eval/results/C_release_decision.md`. The last two gate commands must show Overall PASS and Overall FAIL, respectively.

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

### Commands and expected outputs

| Command | Expected output artifact |
| --- | --- |
| `uvicorn rag.api:app --port 8000` | API stdout includes the query trace JSON lines; requests append to `$TRACE_DIR/traces.jsonl` |
| `Invoke-RestMethod http://127.0.0.1:8000/health` and `curl.exe -sS http://127.0.0.1:8000/metrics` | Health JSON and Prometheus text; captured real run: `eval/results/D1D4_api_run.txt` |
| POST one or more `{ "question": "..." }` requests to `/query` | One trace line per request in `$TRACE_DIR/traces.jsonl`; committed samples: `traces/sample_run.jsonl`, `traces/example.jsonl` |
| `python scripts/audit.py` | PASS/FAIL checklist for repository evidence; Member 2-owned inspection tool is marked M2 |

The D5 trace and five-line diagnosis are in `traces/d5_candidate_fail_sample.jsonl` and `eval/results/D5_root_cause.md`.

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

Every query is appended as one JSON line to `$TRACE_DIR/traces.jsonl` and the same line is printed to stdout. Traces include the full prompt and its SHA-256 hash, retrieved chunk ids, citations, structured guardrail actions, cache state, and latency for each stage. The API abstains with `I don't know based on the documents` when similarity is below `SIMILARITY_THRESHOLD` (default `0.28`) or the safe context does not support the question. `/metrics` returns Prometheus text with request counters and latency / similarity histograms.

On Kubernetes, inspect the most recent persisted trace with:

```sh
kubectl apply -f k8s/trace-inspect-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-trace-inspect --timeout=2m
kubectl -n ragops logs job/ragops-trace-inspect
```

To inspect a specific trace locally, run `python scripts/inspect_trace.py <trace_id> --file traces/k8s_traces_20261127.jsonl`. For a 24-hour trace metrics summary in Kubernetes:

```sh
kubectl apply -f k8s/metrics-window-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-metrics-window --timeout=2m
kubectl -n ragops logs job/ragops-metrics-window
```

## Part E - Live-query coverage and drift

### E3 command sequence and expected outputs

The recorded E3 run compares the same 43-question suite before and after ingesting Batch B:

```powershell
$env:COLLECTION = "e3-before-b-500"
$env:TOP_K = "5"
$env:CHUNK_SIZE = "500"
$env:CHUNK_OVERLAP = "50"
$env:EVAL_ALLOW_MISSING_GROUND_TRUTH = "1"
python -m eval.run_suite --label E3-before-Batch-B --no-gate
$env:DATA_DIR = "data/batch_b"
python -m rag.ingest --data $env:DATA_DIR --collection $env:COLLECTION
$env:EVAL_ALLOW_GROUND_TRUTH_DRIFT = "1"
python -m eval.run_suite --label E3-after-Batch-B --no-gate
```

Expected outputs: the ingestion report `eval/results/verification_<run-id>.json`, two `eval/results/suite_<timestamp>.json`/`.md` pairs, and the comparison `eval/results/E3_drift.md`. The committed before/after runs are `suite_20261126T102138Z` and `suite_20261126T105501Z`.

On Kubernetes, E1 runs the 40-query workload (28 in-domain and 12 out-of-domain) and records query/trace IDs:

```sh
kubectl apply -f k8s/live-query-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-live-queries --timeout=90m
kubectl -n ragops logs job/ragops-live-queries
```

E2/E4 score each query against the golden questions, group uncovered topics, append the six E4 additions, and report the before/after coverage. The threshold is cosine 0.55; the post-addition acceptance floor is 35% to verify the measured increase, while the assignment's 85% example remains the drift alert:

```sh
kubectl apply -f k8s/coverage-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-coverage --timeout=30m
kubectl -n ragops logs job/ragops-coverage
```

The live query log is saved at `eval/results/live_query_log_k8s_20261127.jsonl`; before/after coverage and uncovered-topic evidence are in `eval/results/coverage_k8s_20261127.json`.

## Part F - Kubernetes

The demo must run on Kubernetes; running only Docker containers receives zero. The Kubernetes apply, Job, rollout, rollback, PVC, and port-forward commands are documented in the [Kubernetes runbook](k8s/README.md). The local API Dockerfile is used to build the image consumed by Minikube; Docker-only execution is not a substitute for the Kubernetes demo.

## Part G - Report evidence

Use only real results from `eval/results/` and real JSONL records under `traces/`. The completed submission report is available as [PDF](report/Assignment_03_RAGOps_Report.pdf) and [editable DOCX](report/Assignment_03_RAGOps_Report.docx); it includes the required results, lifecycle and quality-attribute tables, short answers, contributions, AI statement, and screenshot appendix. Supporting results and traces are committed alongside the report.
