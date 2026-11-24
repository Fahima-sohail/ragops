"""Environment configuration with safe repository-local defaults."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]


def _load_local_env() -> None:
    """Load simple KEY=value lines from .env without printing any values."""
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def _path(name: str, default: str) -> Path:
    value = Path(os.environ.get(name, default)).expanduser()
    return (ROOT / value).resolve() if not value.is_absolute() else value.resolve()


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    quarantine_dir: Path
    archive_dir: Path
    trace_dir: Path
    vector_dir: Path
    collection: str
    embed_model: str
    llm_api_key: str
    llm_model: str
    top_k: int
    chunk_size: int
    chunk_overlap: int
    seed: int
    local_device: str
    near_duplicate_threshold: float
    similarity_threshold: float


def get_settings(**overrides: object) -> Settings:
    _load_local_env()
    os.environ.setdefault("HF_HOME", str(ROOT / "data" / "model_cache"))
    if os.environ.get("MODEL_CACHE_OFFLINE", "1").lower() in {"1", "true", "yes"}:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
    values: dict[str, object] = {
        "data_dir": _path("DATA_DIR", "data/batch_a"),
        "quarantine_dir": _path("QUARANTINE_DIR", "data/quarantine"),
        "archive_dir": _path("ARCHIVE_DIR", "data/archive"),
        "trace_dir": _path("TRACE_DIR", "traces"),
        "vector_dir": _path("VECTOR_DIR", "data/vector_store"),
        "collection": os.environ.get("COLLECTION", "ragops"),
        "embed_model": os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        "llm_api_key": os.environ.get("LLM_API_KEY", ""),
        "llm_model": os.environ.get("LLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct"),
        "top_k": int(os.environ.get("TOP_K", "5")),
        "chunk_size": int(os.environ.get("CHUNK_SIZE", "220")),
        "chunk_overlap": int(os.environ.get("CHUNK_OVERLAP", "40")),
        "seed": int(os.environ.get("SEED", "4032")),
        "local_device": os.environ.get("LLM_DEVICE", "cpu"),
        "near_duplicate_threshold": float(os.environ.get("NEAR_DUPLICATE_THRESHOLD", "0.94")),
        "similarity_threshold": float(os.environ.get("SIMILARITY_THRESHOLD", "0.28")),
    }
    values.update(overrides)
    settings = Settings(**values)  # type: ignore[arg-type]
    if settings.top_k < 1:
        raise ValueError("TOP_K must be at least 1")
    if settings.chunk_size < 1 or not 0 <= settings.chunk_overlap < settings.chunk_size:
        raise ValueError("CHUNK_SIZE must be positive and CHUNK_OVERLAP smaller than it")
    if not 0.0 <= settings.near_duplicate_threshold <= 1.0:
        raise ValueError("NEAR_DUPLICATE_THRESHOLD must be between zero and one")
    if not 0.0 <= settings.similarity_threshold <= 1.0:
        raise ValueError("SIMILARITY_THRESHOLD must be between zero and one")
    return settings
