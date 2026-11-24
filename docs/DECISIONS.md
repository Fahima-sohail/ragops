# Decisions

## Scope and source material

- The assignment PDF is the requirements source and is committed as `docs/Assignment_03.pdf`.
- Per the user's latest direction, all implementation and data are authored in this repository. No RAHBAR starter files are modified or copied.
- `data/batch_a` and `data/batch_b` are a locally authored, fictional Aster Research Lab RAG operations corpus for repeatable pipeline tests. Each source states that it is not an official university policy. This avoids presenting invented policy text as real FAST-NUCES material.
- The pipeline itself is implemented with a small set of modules under `rag/`: Markdown/PDF extraction, verification, persistent Chroma storage, local Sentence Transformers embeddings, retrieval, guarded LLM generation, JSONL tracing, and a read-only FastAPI service.

## Evaluation review

- The golden set and human-labelled judge comparisons are drafted in `eval/review/` and marked pending. The assignment's human-authorship/review labels become final only after the user replies `approved`.
- Results produced before that approval are labelled provisional and are not presented as final assignment evidence.

## Member ownership

- `k8s/` remains empty for Member 2.
- Member 2 owns the live-query/coverage scripts, metrics summary script, and trace inspection tool. This repository includes the API metrics endpoint and trace writer/schema only.
