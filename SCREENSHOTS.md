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
