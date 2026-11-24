$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$env:MODEL_CACHE_OFFLINE = "1"
$env:HF_HUB_OFFLINE = "1"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$collection = "a-demo-$stamp"
$env:COLLECTION = $collection
$logPath = Join-Path $repoRoot "eval\results\A_demo_log.txt"
$batchBStage = Join-Path $repoRoot "tmp\a-demo-$stamp\batch-b"
$fullStage = Join-Path $repoRoot "tmp\a-demo-$stamp\full-snapshot"

function Invoke-LoggedPython {
    param(
        [Parameter(Mandatory = $true)][string]$DisplayCommand,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    [System.IO.File]::AppendAllText($logPath, "`r`nPS> $DisplayCommand`r`n", [System.Text.Encoding]::UTF8)
    $commandOutput = & $python @Arguments 2>&1
    $commandExitCode = $LASTEXITCODE
    foreach ($line in $commandOutput) {
        $text = [string]$line
        Write-Output $text
        [System.IO.File]::AppendAllText($logPath, "$text`r`n", [System.Text.Encoding]::UTF8)
    }
    if ($commandExitCode -ne 0) {
        throw "Command failed with exit code ${commandExitCode}: $DisplayCommand"
    }
}

[System.IO.File]::WriteAllText($logPath, "Part A2 demo | collection=$collection | MODEL_CACHE_OFFLINE=$env:MODEL_CACHE_OFFLINE | HF_HUB_OFFLINE=$env:HF_HUB_OFFLINE`r`n", [System.Text.Encoding]::UTF8)
Invoke-LoggedPython "python scripts/build_sample_corpus.py" @("scripts/build_sample_corpus.py")
Invoke-LoggedPython "python -m rag.ingest --data data/batch_a --collection $collection" @("-m", "rag.ingest", "--data", "data/batch_a", "--collection", $collection)
Invoke-LoggedPython "python -m rag.ingest --data data/batch_a --collection $collection" @("-m", "rag.ingest", "--data", "data/batch_a", "--collection", $collection)

New-Item -ItemType Directory -Path $batchBStage -Force | Out-Null
Copy-Item -Path "data\batch_b\*" -Destination $batchBStage -Recurse -Force
Invoke-LoggedPython "python -m rag.ingest --data $($batchBStage.Substring($repoRoot.Length + 1)) --collection $collection" @("-m", "rag.ingest", "--data", $batchBStage, "--collection", $collection)

$queryCode = "from rag.config import get_settings; from rag.retrieve import retrieve; passages, *_ = retrieve('What is the near-duplicate similarity threshold?', get_settings()); print('\n'.join('%s v%s: %s' % (p.doc_id, p.doc_version, p.text) for p in passages if p.doc_id == 'verification-standard'))"
$queryDisplay = 'python -c "' + $queryCode + '"'
Invoke-LoggedPython $queryDisplay @("-c", $queryCode)

New-Item -ItemType Directory -Path $fullStage -Force | Out-Null
Copy-Item -Path "data\batch_a\*" -Destination $fullStage -Recurse -Force
Copy-Item -Path "data\batch_b\*" -Destination $fullStage -Recurse -Force
Remove-Item -LiteralPath (Join-Path $fullStage "source-provenance-v1.0.md") -Force
Invoke-LoggedPython "python -m rag.ingest --data $($fullStage.Substring($repoRoot.Length + 1)) --collection $collection --sync" @("-m", "rag.ingest", "--data", $fullStage, "--collection", $collection, "--sync")
Invoke-LoggedPython "python -m rag.ingest --count-by-doc --collection $collection --doc-id source-provenance" @("-m", "rag.ingest", "--count-by-doc", "--collection", $collection, "--doc-id", "source-provenance")
Invoke-LoggedPython "python -m rag.ingest --restore versioning-standard 1.2 --collection $collection" @("-m", "rag.ingest", "--restore", "versioning-standard", "1.2", "--collection", $collection)
Invoke-LoggedPython $queryDisplay @("-c", $queryCode)
Invoke-LoggedPython "python -m rag.ingest --restore verification-standard 2.1 --collection $collection" @("-m", "rag.ingest", "--restore", "verification-standard", "2.1", "--collection", $collection)
Invoke-LoggedPython $queryDisplay @("-c", $queryCode)

Write-Host "Part A demo log saved to $logPath"
