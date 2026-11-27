# Member 2 — Kubernetes and live operations

## Parts E and F results

The live workload ran as `ragops-live-queries` in Minikube: 40 unique queries (28 in-domain, 12 out-of-domain), with 40 trace IDs recorded. At cosine threshold 0.55, golden-query coverage was 8/40 (20%) before the six E4 additions and 14/40 (35%) afterward. The six new unreviewed synthetic abstention questions cover six out-of-domain topics; 26 live questions remain below threshold. The committed before/after output lists the uncovered query topics. The 35% post-addition exit floor confirms the measured increase; the assignment's 85% example remains the drift alert.

The API runs as a Deployment behind a ClusterIP Service. Its Chroma directory, both data batches, quarantine, archive, traces, and evaluation results use the 12 GiB `ragops-data` PVC. The API endpoints only retrieve, while `rag.ingest` is the vector record writer. Embedded Chroma opens a SQLite journal/lock during retrieval, so the API's PVC mount must be writable even though API code does not add, update, or delete vectors. The recurring Batch B CronJob succeeded: it found the same 8 valid documents, skipped all 24 unchanged chunks, embedded 0 chunks, and quarantined the same six invalid/duplicate files.

The measured baseline Kubernetes suite (`e3-before-b-500`, TOP_K=3) ran all three evaluation levels and returned exit status 1 because its actual p95 (91,226.9 ms) exceeded the initial offline-calibrated 36,500 ms gate and citation validity (0.8889) was below 0.90. That is the expected F2 fail-fast behavior. The passing candidate Kubernetes suite (`cand_topk8`, TOP_K=8) measured recall@5 0.958333, faithfulness 1.0, correct abstention 1.0, citation validity 0.972222, p50 32,239.514 ms, and p95 70,173.7 ms. Against the same Minikube baseline, a 20% latency allowance is 109,472.28 ms; the ConfigMap rounds that ceiling up to 109,500 ms. With only the ConfigMap ceiling changed, the candidate passed all five release checks. The initial ceiling first blocked the candidate; the high-citation-floor fixture also shows a ConfigMap-only failure without an image rebuild. A separate failing C2 fixture remained gated and was never rolled out.

After the measured gate passed, the candidate Deployment was rolled into the live Deployment using `maxUnavailable: 0` and observed with `kubectl rollout status`. The candidate API Deployment was scaled to zero after evaluation to free its 2 GiB reservation for the rolling surge; the candidate collection and Service remain defined. A deliberate high-threshold update (`TOP_K=1`, similarity floor 0.99) produced an abstention. `kubectl rollout undo` restored the prior release, and a fresh query trace identifies `cand_topk8` and `sentence-transformers/all-MiniLM-L6-v2; sentence-transformers=3.4.1`.

The 24-hour trace summary covered 143 real records: abstention rate 41.96%, cache-hit rate 0%, three injection removals, total-latency p95 91,754.626 ms, generation p95 91,606.249 ms, retrieval p95 23.595 ms, and top-1 similarity p50/p95 0.521428/0.729602. The trace inspection Job reconstructed the exact prompt and all eight retrieved chunks for the post-rollback trace.

### Measured Kubernetes resources

`kubectl top` during CPU model generation measured the baseline API at approximately 1.9–1.99 CPU cores and 3.5 GiB RAM; the candidate evaluation container used approximately 1.9–1.99 cores and 3.0–3.2 GiB. API requests are 1 CPU / 2 GiB with limits of 2 CPU / 5 GiB. Evaluation requests are 1 CPU / 3 GiB with limits of 2 CPU / 5 GiB. Ingestion requests are 1 CPU / 2 GiB with limits of 2 CPU / 4 GiB. The live-query runner requests 250m CPU / 256 MiB with limits of 1 CPU / 1 GiB. The 12 GiB PVC remained Bound throughout.

## Evidence files

- Minikube coverage report and 40-query output: `eval/results/coverage_k8s_20261127.json`, `eval/results/live_query_log_k8s_20261127.jsonl`.
- Baseline/candidate Kubernetes suite outputs: `eval/results/suite_k8s_baseline_20261127.*`, `eval/results/suite_k8s_candidate_20261127.*`.
- Gate fail/pass, CronJob, ingestion, verification, trace inspection, and resource summary: `eval/results/k8s_*_20261127.*`.
- Cluster JSONL traces, including the post-rollback trace: `traces/k8s_traces_20261127.jsonl`.
- Minikube manifests and exact run commands: `k8s/` and `k8s/README.md`.

## Screenshot appendix checklist

Capture uncropped terminal screenshots from the running Minikube cluster and save them in `report/screenshots/`, labeled A1, A2, B, C2, D1, D2, E2/E4, F1/F2/F3/F4/F5. The screenshot checklist and exact evidence views are in `k8s/README.md`.
