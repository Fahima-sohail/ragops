# Screenshot commands

## Part A

Run these commands from the repository root in PowerShell with `.venv` active. They keep model downloads offline and create a unique collection and staging path for this capture session.

```powershell
$env:MODEL_CACHE_OFFLINE = "1"
$env:HF_HUB_OFFLINE = "1"
$shotRun = Get-Date -Format "yyyyMMdd-HHmmss"
$env:COLLECTION = "part-a-shot-$shotRun"
$batchB = "tmp\part-a-$shotRun\batch-b"
$fullSnapshot = "tmp\part-a-$shotRun\full-snapshot"
python scripts/build_sample_corpus.py
python -m rag.ingest --data data\batch_a --collection $env:COLLECTION
python -m rag.ingest --data data\batch_a --collection $env:COLLECTION
New-Item -ItemType Directory -Force $batchB | Out-Null
Copy-Item data\batch_b\* $batchB -Recurse -Force
python -m rag.ingest --data $batchB --collection $env:COLLECTION
python -c "from rag.config import get_settings; from rag.retrieve import retrieve; p, *_ = retrieve('What is the near-duplicate similarity threshold?', get_settings()); print('\n'.join('%s v%s: %s' % (x.doc_id, x.doc_version, x.text) for x in p if x.doc_id == 'verification-standard'))"
New-Item -ItemType Directory -Force $fullSnapshot | Out-Null
Copy-Item data\batch_a\* $fullSnapshot -Recurse -Force
Copy-Item data\batch_b\* $fullSnapshot -Recurse -Force
Remove-Item "$fullSnapshot\source-provenance-v1.0.md" -Force
python -m rag.ingest --data $fullSnapshot --collection $env:COLLECTION --sync
python -m rag.ingest --count-by-doc --collection $env:COLLECTION --doc-id source-provenance
python -m rag.ingest --restore verification-standard 2.1 --collection $env:COLLECTION
python -c "from rag.config import get_settings; from rag.retrieve import retrieve; p, *_ = retrieve('What is the near-duplicate similarity threshold?', get_settings()); print('\n'.join('%s v%s: %s' % (x.doc_id, x.doc_version, x.text) for x in p if x.doc_id == 'verification-standard'))"
```

For the same full sequence with its actual terminal output saved to `eval/results/A_demo_log.txt`, run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_a_demo.ps1` from the repository root.

## Part B - Offline evaluation and release gate

Run from the repository root with `.venv` active. This uses the Part A collection and cached models in offline mode. The suite command runs embedding, clean/noise/typo retrieval, and LLM-judged end-to-end evaluation. On its first run it creates `eval/results/baseline.json` from those real metrics; later runs compare to that baseline and return exit code 1 if the gate fails.

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

The suite writes `suite_<timestamp>.json` and `.md`, prints its metric and gate tables, and creates `eval/judge_labels.csv` once with ten sampled answers for manual labels. After labeling at least eight rows, run `python -m eval.judge_agreement`; with fewer than eight labels it exits 1 with the count and next step. `python -m eval.run_suite --no-gate` writes the same reports while skipping the gate. The standalone `python -m eval.module_embedding` and `python -m eval.component_retrieval` commands remain available for focused reports. The retrieval noise documents are added only to an ephemeral collection.

### Part C1/C2 - top-k candidate and release gate

Chunk-size 500 and 250 produced identical chunk counts because every corpus page is shorter than 250 words, so C1 uses the allowed measurable change: TOP_K 3 versus 8. Baseline and candidate collections contain the same Batch A + Batch B documents chunked at 500/50. The deliberate failing candidate uses TOP_K=1 and SIMILARITY_THRESHOLD=0.99. The measured comparison, gate outputs, and release decision are committed in `eval/results/C1_comparison.md`, `C2_gate_pass.txt`, `C2_gate_fail.txt`, and `C_release_decision.md`.

```powershell
$env:MODEL_CACHE_OFFLINE = "1"
$env:HF_HUB_OFFLINE = "1"
$env:LLM_API_KEY = ""
$env:SEED = "4032"
$env:VECTOR_DIR = "data/vector_store"
$env:CHUNK_SIZE = "500"
$env:CHUNK_OVERLAP = "50"
$env:SIMILARITY_THRESHOLD = "0.28"
$env:COLLECTION = "e3-before-b-500"
$env:TOP_K = "3"
python -m eval.run_suite --label C1-baseline-topk3 --no-gate
$env:COLLECTION = "cand_topk8"
$env:TOP_K = "8"
python -m rag.ingest --data data\batch_a --collection $env:COLLECTION
New-Item -ItemType Directory -Force tmp\c1-batch-b-topk8 | Out-Null
Copy-Item data\batch_b\* tmp\c1-batch-b-topk8 -Recurse -Force
python -m rag.ingest --data tmp\c1-batch-b-topk8 --collection $env:COLLECTION
python -m eval.run_suite --label C1-candidate-topk8 --no-gate
$env:COLLECTION = "cand_topk1"
$env:TOP_K = "1"
$env:SIMILARITY_THRESHOLD = "0.99"
python -m rag.ingest --data data\batch_a --collection $env:COLLECTION
New-Item -ItemType Directory -Force tmp\c2-batch-b-topk1 | Out-Null
Copy-Item data\batch_b\* tmp\c2-batch-b-topk1 -Recurse -Force
python -m rag.ingest --data tmp\c2-batch-b-topk1 --collection $env:COLLECTION
python -m eval.run_suite --label C2-deliberate-fail-topk1 --no-gate
python -m eval.gate --candidate eval/results/C2_candidate_pass.json --baseline eval/results/C2_baseline.json --config gate.yaml
python -m eval.gate --candidate eval/results/C2_candidate_fail.json --baseline eval/results/C2_baseline.json --config gate.yaml
```

The recorded artifacts are `eval/results/C1_comparison.md`, `C2_gate_pass.txt`, `C2_gate_fail.txt`, and `C_release_decision.md`. For mounted thresholds, set `$env:GATE_CONFIG` to the mounted YAML path; `python -m eval.gate` reads it unless `--config` is provided.

## Part D1/D4

Use the Part A demo collection printed in `eval/results/A_demo_log.txt`. In the API server PowerShell window, ingest the Batch B injection fixture (it is unchanged if Part A has already indexed it), keep model access offline, and start the API:

```powershell
$env:COLLECTION = "a-demo-20261125-012139"
$env:TRACE_DIR = "tmp\d1d4-api-traces"
$env:MODEL_CACHE_OFFLINE = "1"
$env:HF_HUB_OFFLINE = "1"
New-Item -ItemType Directory -Force tmp\d4-injection | Out-Null
Copy-Item data\batch_b\injection-test-record-v1.0.md tmp\d4-injection -Force
python -m rag.ingest --data tmp\d4-injection --collection $env:COLLECTION
uvicorn rag.api:app --host 127.0.0.1 --port 8000
```

In a second PowerShell window, set the same environment and run three curl requests. The first retrieves the injected record, the second asks a grounded question, and the third repeats it to show a cache hit:

```powershell
$env:COLLECTION = "a-demo-20261125-012139"
$env:TRACE_DIR = "tmp\d1d4-api-traces"
$env:MODEL_CACHE_OFFLINE = "1"
$env:HF_HUB_OFFLINE = "1"
curl.exe -sS http://127.0.0.1:8000/health
Set-Content -LiteralPath tmp\d4-q1.json -Value '{"question":"What should the incident reviewer verify after a prompt injection test?"}' -Encoding Ascii -NoNewline
curl.exe -sS -X POST http://127.0.0.1:8000/query -H "Content-Type: application/json" --data-binary "@tmp\d4-q1.json"
Set-Content -LiteralPath tmp\d4-q2.json -Value '{"question":"Which component is allowed to write to the vector store?"}' -Encoding Ascii -NoNewline
curl.exe -sS -X POST http://127.0.0.1:8000/query -H "Content-Type: application/json" --data-binary "@tmp\d4-q2.json"
curl.exe -sS -X POST http://127.0.0.1:8000/query -H "Content-Type: application/json" --data-binary "@tmp\d4-q2.json"
curl.exe -sS http://127.0.0.1:8000/metrics
```

Each request writes one line to `$TRACE_DIR/traces.jsonl` and prints that identical JSON line in the server console. The committed real sample is `traces/sample_run.jsonl`.


### Part D5 - trace-only root cause

Use the trace id and relevant fields in the report, then inspect the exact matching JSONL record.

```powershell
$traceId = "76fd2f54-75b9-4c06-b14d-052096584939"
Select-String -Path traces\traces.jsonl -Pattern $traceId
Get-Content eval\results\D5_root_cause.md
```

### Part E3 - Batch B drift

The E3 suites run on the same collection and settings before and after Batch B ingestion. The pre-Batch-B run enables `EVAL_ALLOW_MISSING_GROUND_TRUTH=1` so Batch-B-only reference pages count as absent instead of aborting the retrieval level. After ingestion, `EVAL_ALLOW_GROUND_TRUTH_DRIFT=1` records references changed by a newer document version as unverified while still measuring doc/page retrieval.

```powershell
$env:MODEL_CACHE_OFFLINE = "1"
$env:HF_HUB_OFFLINE = "1"
$env:LLM_API_KEY = ""
$env:COLLECTION = "e3-before-b-500"
$env:CHUNK_SIZE = "500"
$env:CHUNK_OVERLAP = "50"
$env:TOP_K = "5"
$env:EVAL_ALLOW_MISSING_GROUND_TRUTH = "1"
python -m rag.ingest --data data/batch_a --collection $env:COLLECTION
python -m eval.run_suite --label E3-before-Batch-B --no-gate
New-Item -ItemType Directory -Force tmp\e3-batch-b | Out-Null
Copy-Item data\batch_b\* tmp\e3-batch-b -Recurse -Force
python -m rag.ingest --data tmp\e3-batch-b --collection $env:COLLECTION
Remove-Item Env:EVAL_ALLOW_MISSING_GROUND_TRUTH
$env:EVAL_ALLOW_GROUND_TRUTH_DRIFT = "1"
python -m eval.run_suite --label E3-after-Batch-B-C1-baseline500 --no-gate
Remove-Item Env:EVAL_ALLOW_GROUND_TRUTH_DRIFT
Get-Content eval\results\E3_drift.md
```
