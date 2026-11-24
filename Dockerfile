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
    HF_HOME=/app/data/model_cache \
    MODEL_CACHE_OFFLINE=1

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY scripts ./scripts
RUN python scripts/download_models.py --allow-download
COPY rag ./rag
COPY eval ./eval
COPY gate.yaml .
COPY data ./data
COPY traces ./traces

EXPOSE 8000
CMD ["uvicorn", "rag.api:app", "--host", "0.0.0.0", "--port", "8000"]
