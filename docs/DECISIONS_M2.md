# Member 2 implementation decisions

## 2026-11-27 — M0 image and cluster

- Use Python 3.13 slim because `requirements.txt` states those pins were tested with Python 3.13.
- Build the image inside Minikube with `minikube image build -t ragops:v1 .`; this places the image in the cluster runtime without a registry.
- Install the pinned CPU PyTorch wheel. The first ARM64 build selected CUDA dependencies and failed `pip check` on `nvidia-cusparselt-cu13`; the CPU wheel made dependency validation clean and fits the CPU-only Minikube profile.
- Store model snapshots at `/models`, use offline Hugging Face and Transformers variables at runtime, and symlink `/app/data/model_cache` to `/models` because the existing embedding and generation modules explicitly use that repository path.
- Keep the model cache in a BuildKit cache mount during image construction, then copy it into `/models` in the final image. If `data/model_cache` already contains models, the existing downloader verifies the snapshots locally and skips downloading them.
- M0 acceptance: Minikube image listing showed `docker.io/library/ragops:v1`; `python -m rag.ingest --help` and `import rag.api` each succeeded in one-off Minikube pods. Final image size reported by Minikube CRI was 2.08 GB.

## Screenshot capture rule

The M0 image checks are shown by their real command outputs and are not listed as required assignment screenshots. Capture the assignment's A-F screenshot items directly from terminal output when those cluster evidence runs are performed; record actual files under `report/screenshots/`. Do not create screenshots or measurement claims from local simulations.
