# Report evidence map

The Member 1 report draft is [`member1_sections.md`](member1_sections.md). Every measured value there cites a committed file under `eval/results/` or `traces/`.

- Part A verification and ingestion runs: `eval/results/verification_*.json`, `eval/results/A_demo_log.txt`, and `data/batch_b/PLANTED.md`.
- Part B module, component, and end-to-end metrics: timestamped `eval/results/suite_*.json` and Markdown summaries; judge agreement and stochasticity have their own timestamped result files.
- Part C: `eval/results/C1_comparison.md`, `C2_gate_pass.txt`, `C2_gate_fail.txt`, and `C_release_decision.md`.
- Part D: `eval/results/D1D4_api_run.txt`, `eval/results/D5_root_cause.md`, and real JSONL records under `traces/`.
- Part E3: `eval/results/E3_drift.md`, its before/after suite files, and `traces/e3_batch_b_sample.jsonl`.
- Part E1, E2, and E4, the trace inspection tool, and Part F Kubernetes evidence are owned by Member 2 and are not claimed as completed here.

The user confirmed review of the ten human golden questions and ten judge labels. The golden-set review indicators and judge agreement output record that status.
