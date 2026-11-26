# Part C release decision: release TOP_K=8

**Decision: RELEASE the TOP_K=8 candidate** (`cand_topk8`, `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`, `SIMILARITY_THRESHOLD=0.28`, seed 4032), subject to Member 2 using these same values in the candidate Deployment.

The full candidate suite is `suite_20261126T161600Z.json`; it passed all five rules against the measured TOP_K=3 baseline `suite_20261126T155753Z.json`. The recorded CLI output is `C2_gate_pass.txt`: recall@5 drop 0.000000 (limit 0.020000), faithfulness 1.0 (minimum 0.95), citation validity 0.972222 (minimum 0.90), p95 latency 27,204.269 ms (maximum 36,500 ms), and abstention correctness 1.0 (baseline 1.0).

C1 changed only `TOP_K` and the collection selection. Mean end-to-end context grew from 3 to 8 chunks per question; citation validity improved from 0.888889 to 0.972222, false-abstention rate fell from 0.111111 to 0.027778, and p95 latency fell from 30,392.909 ms to 27,204.269 ms. The component rank metrics stayed equal because that evaluation measures the collection's full ranked list; the configured cap changes the context passed to end-to-end generation.

**Reject the deliberate TOP_K=1 / similarity-threshold 0.99 candidate** (`cand_topk1`). Its full suite is `suite_20261126T162002Z.json` and its CLI output is `C2_gate_fail.txt`. The candidate abstained on all 36 answer-expected questions, had false-abstention rate 1.0 and citation validity 0.0, and failed the citation rule. Its p95 is very low because it performs no generation; that speed is not a quality improvement. Faithfulness is 1.0 under the suite's vacuous-truth treatment of abstentions, so the release decision also considers the reported false-abstention and citation metrics.

The measured TOP_K=3 baseline had faithfulness 1.0 and p95 30,392.909 ms. `gate.yaml` therefore sets faithfulness to at least 0.95 and p95 to at most 36,500 ms (20% over the measured p95, rounded up). Recall@5 may fall by at most 0.02 and abstention correctness may not fall below baseline. The rule-by-rule gate tests passed in `tests/test_eval_gate.py`.
