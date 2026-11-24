"""Cache configured Hugging Face models without replacing existing snapshots."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embed-model", default=os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    parser.add_argument("--llm-model", default=os.environ.get("LLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct"))
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--allow-download", action="store_true", help="download only models missing from the local cache")
    args = parser.parse_args()
    cache_dir = ROOT / "data" / "model_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    models = [args.embed_model] + ([] if args.skip_llm else [args.llm_model])
    for model in models:
        try:
            location = snapshot_download(repo_id=model, cache_dir=str(cache_dir), local_files_only=True)
            print(f"Already cached: {model} ({location})", flush=True)
        except Exception as exc:
            if not args.allow_download:
                raise RuntimeError(
                    f"{model} is not cached; enable --allow-download when network access is available"
                ) from exc
            print(f"Downloading missing model: {model}", flush=True)
            location = snapshot_download(repo_id=model, cache_dir=str(cache_dir))
            print(f"Cached: {model} ({location})", flush=True)


if __name__ == "__main__":
    main()
