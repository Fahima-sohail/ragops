"""Download configured Hugging Face models once for network-free local runs."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embed-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--llm-model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--skip-llm", action="store_true")
    args = parser.parse_args()
    cache_dir = ROOT / "data" / "model_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(cache_dir)
    os.environ.pop("HF_HUB_OFFLINE", None)
    models = [args.embed_model] + ([] if args.skip_llm else [args.llm_model])
    for model in models:
        print(f"Caching public model: {model}", flush=True)
        location = snapshot_download(repo_id=model, cache_dir=str(cache_dir))
        print(f"Cached {model} at {location}", flush=True)


if __name__ == "__main__":
    main()
