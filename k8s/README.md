# RAGOps Kubernetes runbook

Run the assignment demo on Minikube with the Docker driver. Prerequisites: Docker Desktop running, Minikube, kubectl, and at least 4 CPUs / 6 GiB RAM allocated to the cluster. This uses a single persistent volume for the data lake, Chroma database, archive, quarantine, traces, and evaluation results. The API mounts the vector directory read-only; ingestion Jobs are the only vector-store writers. The image is shared by API and Jobs.

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

The image build runs `scripts/download_models.py --allow-download`; it downloads only snapshots absent from the image cache. The cluster is then offline for model access. To use a hosted LLM, create the optional `ragops-secrets` Secret with `LLM_API_KEY`; no secret values belong in this repository. The default local model needs no secret.

## Part A ingestion and Part B evaluation Jobs

```sh
kubectl apply -f k8s/eval-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-eval --timeout=90m
kubectl -n ragops logs job/ragops-eval
kubectl -n ragops get pvc,job,cronjob,pod
```

Run the Batch B update as a Kubernetes Job by changing the `--data` value in `k8s/ingest-job.yaml` to `/app/data/batch_b` and the job name to `ragops-ingest-b`, then apply it. This runs verification, incremental update, archive, and quarantine against the same persistent collection. Delete the completed Job object before reapplying a changed Job spec.

Schedule recurring Batch A synchronization with:

```sh
kubectl apply -f k8s/ingest-cronjob.yaml
```

## Part C candidate, gate, rollout, and rollback

The candidate collection uses the C1 `TOP_K=8` setting. Build the identical application as the candidate image tag, ingest both snapshots into its own collection, then evaluate it:

```sh
minikube image build -t ragops:candidate .
kubectl apply -f k8s/candidate-ingest-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-candidate-ingest --timeout=90m
kubectl apply -f k8s/candidate-api.yaml
kubectl -n ragops rollout status deployment/ragops-candidate
kubectl apply -f k8s/candidate-eval-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-candidate-eval --timeout=90m
kubectl -n ragops logs job/ragops-candidate-eval
```

Apply the threshold ConfigMap and run the recorded measured gate fixtures:

```sh
kubectl apply -f k8s/config.yaml
kubectl apply -f k8s/gate-job.yaml
kubectl -n ragops wait --for=condition=complete job/ragops-gate --timeout=2m
kubectl -n ragops logs job/ragops-gate
```

To demonstrate that the ConfigMap controls the result without a rebuild, edit `min_citation_validity` in `k8s/config.yaml` under `ragops-gate`, reapply it, delete the completed gate Job, and repeat the gate commands. The measured passing candidate's citation validity is in `eval/results/C2_candidate_pass.json`; set the floor above that value to make it fail. Restore the committed 0.90 threshold before release.

After the candidate evaluation and passing gate, apply `k8s/rollout.yaml` and watch the live rollout. To demonstrate rollback, set the API image to the bad image tag, then undo and issue a query; the resulting trace must name the prior collection and embedding model/version.

```sh
kubectl apply -f k8s/rollout.yaml
kubectl -n ragops rollout status deployment/ragops-api
kubectl -n ragops rollout undo deployment/ragops-api
kubectl -n ragops rollout status deployment/ragops-api
```

## Parts D and E live query, coverage, and trace commands

```sh
kubectl -n ragops port-forward service/ragops-api 8000:8000
python -m eval.run_live_queries --url http://127.0.0.1:8000
python -m eval.coverage --threshold 0.55 --minimum 0.85
python -m eval.coverage --threshold 0.55 --minimum 0.85 --additions eval/coverage_additions.jsonl --output eval/results/coverage_after.json
python scripts/summarize_metrics.py --last-hours 24
python scripts/inspect_trace.py TRACE_ID
kubectl -n ragops logs deployment/ragops-api
```

The 40-query workload contains 28 in-domain and 12 out-of-domain questions. The coverage command compares each query with its nearest golden question by cosine similarity. E4 additions are merged into `eval/golden.jsonl` as unreviewed synthetic abstention questions; evaluate the expanded suite with the same Part B Job after applying it.

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
