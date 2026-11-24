"""Local Sentence Transformers embeddings and cosine helpers."""

from __future__ import annotations

from functools import lru_cache
import importlib.metadata
import os
import time
from typing import Sequence

import numpy as np
from rag.config import ROOT


@lru_cache(maxsize=2)
def _model(model_name: str, device: str):
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, cache_folder=str(ROOT / "data" / "model_cache"), device=device)


def embedding_version(model_name: str) -> str:
    try:
        library_version = importlib.metadata.version("sentence-transformers")
    except importlib.metadata.PackageNotFoundError:
        library_version = "unknown"
    return f"{model_name}; sentence-transformers={library_version}"


def embed_texts(texts: Sequence[str], model_name: str, device: str = "cpu") -> tuple[list[list[float]], float]:
    if not texts:
        return [], 0.0
    model = _model(model_name, device)
    started = time.perf_counter()
    vectors = model.encode(
        list(texts),
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=32,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return np.asarray(vectors, dtype=np.float32).tolist(), elapsed_ms


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    a = np.asarray(left, dtype=np.float64)
    b = np.asarray(right, dtype=np.float64)
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denominator) if denominator else 0.0
