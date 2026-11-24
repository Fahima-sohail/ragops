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
