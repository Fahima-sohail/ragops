# syntax=docker/dockerfile:1.7
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data/batch_a \
    QUARANTINE_DIR=/app/data/quarantine \
    ARCHIVE_DIR=/app/data/archive \
    TRACE_DIR=/app/traces \
    VECTOR_DIR=/app/data/vector_store \
    COLLECTION=ragops \
    EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2 \
    LLM_MODEL=Qwen/Qwen2.5-0.5B-Instruct \
    TOP_K=5 \
    CHUNK_SIZE=220 \
    CHUNK_OVERLAP=40 \
    SEED=4032 \
    HF_HOME=/models \
    HF_HUB_CACHE=/models \
    MODEL_CACHE_DIR=/models \
    SENTENCE_TRANSFORMERS_HOME=/models \
    TRANSFORMERS_CACHE=/models \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    MODEL_CACHE_OFFLINE=1

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt \
    && python -m pip check \
    && python -c "import torch; assert torch.version.cuda is None, torch.version.cuda; print('CPU PyTorch:', torch.__version__)"
COPY scripts ./scripts
COPY rag ./rag
COPY eval ./eval
COPY gate.yaml .
COPY data/batch_a ./data/batch_a
COPY data/batch_b ./data/batch_b
COPY data/model_cache/ /models/
RUN --mount=type=cache,id=ragops-model-cache,target=/model-cache \
    cp -a /models/. /model-cache/ \
    && mkdir -p /app/data \
    && ln -s /model-cache /app/data/model_cache \
    && HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 MODEL_CACHE_OFFLINE=0 \
    python scripts/download_models.py --allow-download \
    && rm /app/data/model_cache \
    && cp -a /model-cache/. /models/ \
    && ln -s /models /app/data/model_cache

EXPOSE 8000
CMD ["uvicorn", "rag.api:app", "--host", "0.0.0.0", "--port", "8000"]
