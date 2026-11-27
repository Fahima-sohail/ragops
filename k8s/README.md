# RAGOps Kubernetes runbook

Run the assignment demo on Minikube with the Docker driver. Prerequisites: Docker Desktop running, Minikube, kubectl, and at least 4 CPUs / 6 GiB RAM allocated to the cluster. This uses a single persistent volume for the data lake, Chroma database, archive, quarantine, traces, and evaluation results. The API routes are retrieval-only; the embedded Chroma PersistentClient needs a writable SQLite lock/journal, so the API's vector mount is read-write. The image is shared by API and Jobs.

## Build and initialize

```sh
minikube start --driver=docker --cpus=4 --memory=6g --disk-size=30g
minikube image build -t ragops:v1 .
minikube image ls | grep ragops
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/storage.yaml
kubectl apply -f k8s/config.yaml
kubectl apply -f k8s/seed-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-seed-data --timeout=10m
kubectl apply -f k8s/ingest-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-ingest --timeout=45m
kubectl -n ragops logs job/ragops-ingest
kubectl apply -f k8s/api.yaml
kubectl -n ragops rollout status deployment/ragops-api
```

The image build runs `scripts/download_models.py --allow-download`; it downloads only snapshots absent from the image cache. The model cache is retained in the BuildKit cache across builds and is baked into `/models`; the cluster is then offline for model access. The API exposes retrieval-only routes, but the embedded Chroma PersistentClient needs a writable SQLite lock/journal on the persistent volume; therefore its vector mount is read-write. To use a hosted LLM, create the optional `ragops-secrets` Secret with `LLM_API_KEY`; no secret values belong in this repository. The default local model needs no secret.

## Part A ingestion and Part B evaluation Jobs

```sh
kubectl apply -f k8s/eval-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-eval --timeout=90m
kubectl -n ragops logs job/ragops-eval
kubectl -n ragops get pvc,job,cronjob,pod
```

Run Batch B as its own Kubernetes Job. It runs verification, incremental update, archive, and quarantine against the same persistent collection:

```sh
kubectl apply -f k8s/ingest-batch-b-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-ingest-b --timeout=45m
kubectl -n ragops logs job/ragops-ingest-b
kubectl apply -f k8s/verification-report-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-verification-report --timeout=2m
kubectl -n ragops logs job/ragops-verification-report
```

Schedule recurring Batch A synchronization with:

```sh
kubectl apply -f k8s/ingest-cronjob.yaml
```

## Part C candidate, gate, rollout, and rollback

The baseline uses the measured C2 `TOP_K=3`, `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50` settings in `e3-before-b-500`. The candidate collection uses the same corpus/chunk/embedding/seed settings and `TOP_K=8`. Ingest both snapshots into its own collection, then evaluate it:

```sh
kubectl apply -f k8s/candidate-ingest-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-candidate-ingest --timeout=90m
kubectl apply -f k8s/candidate-api.yaml
kubectl -n ragops rollout status deployment/ragops-candidate
kubectl apply -f k8s/candidate-eval-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-candidate-eval --timeout=90m
kubectl -n ragops logs job/ragops-candidate-eval
```

The candidate suite writes its metrics to `eval/results/candidate.json`. Snapshot the latest completed TOP_K=3 Kubernetes suite before running the candidate so both gate inputs use the same current corpus and golden set:

```sh
kubectl apply -f k8s/snapshot-baseline-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-snapshot-k8s-baseline --timeout=2m
kubectl -n ragops logs job/ragops-snapshot-k8s-baseline
```

Apply the threshold ConfigMap and run the gate against the paired Kubernetes results:

```sh
kubectl apply -f k8s/config.yaml
kubectl apply -f k8s/gate-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-gate --timeout=2m
kubectl -n ragops logs job/ragops-gate
```

The initial offline gate ceiling is 36,500 ms. On this 4 CPU / 6 GiB Minikube profile, the measured TOP_K=3 baseline suite p95 was 91,226.9 ms; use a 20 percent allowance (109,500 ms rounded up) for cluster release decisions. First run the candidate against the original ceiling, then update only `ragops-gate` in `k8s/config.yaml` to the measured cluster ceiling and rerun the same candidate. The deliberate failing candidate and tighter citation ConfigMap are available to show additional fail/pass outcomes without rebuilding:

```sh
kubectl apply -f k8s/gate-initial-config.yaml -f k8s/gate-initial-job.yaml
kubectl -n ragops wait --for=condition=failed job/ragops-gate-initial --timeout=2m
kubectl -n ragops logs job/ragops-gate-initial
kubectl apply -f k8s/config.yaml
kubectl -n ragops delete job ragops-gate
kubectl apply -f k8s/gate-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-gate --timeout=2m
kubectl -n ragops logs job/ragops-gate
kubectl apply -f k8s/gate-fail-fixture-job.yaml
kubectl -n ragops wait --for=condition=failed job/ragops-gate-fail-fixture --timeout=2m
kubectl -n ragops logs job/ragops-gate-fail-fixture
kubectl apply -f k8s/gate-pass-fixture-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-gate-pass-fixture --timeout=2m
kubectl -n ragops logs job/ragops-gate-pass-fixture
kubectl apply -f k8s/gate-tight-config.yaml -f k8s/gate-tight-fixture-job.yaml
kubectl -n ragops wait --for=condition=failed job/ragops-gate-tight-fixture --timeout=2m
kubectl -n ragops logs job/ragops-gate-tight-fixture
```

After the candidate evaluation and passing gate, apply `k8s/rollout.yaml` and watch the live rollout. To demonstrate rollback, apply the deliberate high-threshold candidate configuration, issue a query, undo the release, and issue another query; the second trace must name the prior collection and embedding model/version.

```sh
kubectl -n ragops scale deployment/ragops-candidate --replicas=0
kubectl apply -f k8s/rollout.yaml
kubectl -n ragops rollout status deployment/ragops-api
kubectl apply -f k8s/bad-rollout.yaml
kubectl -n ragops rollout status deployment/ragops-api
kubectl -n ragops rollout undo deployment/ragops-api
kubectl -n ragops rollout status deployment/ragops-api
```

## Parts D and E live query, coverage, and trace commands

```sh
kubectl apply -f k8s/live-query-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-live-queries --timeout=90m
kubectl -n ragops logs job/ragops-live-queries
kubectl apply -f k8s/coverage-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-coverage --timeout=30m
kubectl -n ragops logs job/ragops-coverage
kubectl apply -f k8s/metrics-window-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-metrics-window --timeout=2m
kubectl -n ragops logs job/ragops-metrics-window
kubectl apply -f k8s/trace-inspect-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-trace-inspect --timeout=2m
kubectl -n ragops logs job/ragops-trace-inspect
kubectl -n ragops port-forward service/ragops-api 8000:8000
curl http://127.0.0.1:8000/metrics
kubectl -n ragops logs deployment/ragops-api
```

The 40-query workload contains 28 in-domain and 12 out-of-domain questions. The coverage command compares each query with its nearest golden question by cosine similarity. E4 additions are merged into `eval/golden.jsonl` as unreviewed synthetic abstention questions. The pre-E4 report uses the assignment example's 85% drift alert; the post-E4 Job uses a 35% minimum to verify the measured 15-point increase (20% to 35%), while still reporting uncovered queries and topic groups.

## Screenshot evidence for Parts A to F

The M0 image build is acceptance evidence, but it is not one of the assignment's required report screenshots. For the submission screenshots, capture the command and its complete, uncropped output after each run; save original images under `report/screenshots/` and include them in the report appendix.

| Assignment item | Screenshot evidence |
| --- | --- |
| A1 | Batch B verification report showing each check and its reason |
| A2 | Second ingestion of an unchanged corpus showing zero embedded chunks |
| B | Evaluation summary showing embedding, retrieval, and end-to-end metrics |
| C2 | One failing and one passing release gate |
| D1/D2 | A complete JSONL trace and the trace inspection command rebuilding its prompt and context |
| E2/E4 | Coverage output before and after adding the six golden questions |
| F1/F4 | `kubectl -n ragops get all,pvc,configmap,cronjob,job`; `kubectl port-forward` and `/metrics` output |
| F2 | Completed `ragops-ingest` and `ragops-eval` Job logs, including exit status |
| F2 gate | Gate Job output before and after changing the ConfigMap threshold |
| F3 | Candidate evaluation, gate pass, `rollout status`, `rollout undo`, then query response/trace showing old collection and embedding version |
| F5 | `kubectl top pods` during API and Job runs, plus pod resource requests/limits; record actual measurements in the report |

Do not create screenshot substitutes or report resource figures until they come from the running Minikube cluster.
