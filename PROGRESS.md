# Progress

## 2026-11-24

- Initialized this repository on `main` and configured the empty GitHub repository `Fahima-sohail/ragops` as `origin`.
- Copied the complete Assignment 03 PDF to `docs/Assignment_03.pdf` and extracted all five pages to `docs/assignment_03_extracted.txt` for searchable local reference.
- Following the user's latest direction, implementation and data will be created only inside this repository. No RAHBAR starter files are being changed or copied.
- Current step: build the self-contained RAGOps implementation and locally authored, clearly fictional sample corpus. Human-review labels remain drafts pending the user's `approved` reply.

## 2026-11-25

- Read `AGENTS.md`, `PROGRESS.md`, and Git history before continuing. `main` and `origin/main` are synchronized at `6db81b0`; there were no unpushed commits or local edits.
- Confirmed both local model snapshots already exist under ignored `data/model_cache/`. Keep `MODEL_CACHE_OFFLINE=1`; do not download them again.
- Added `scripts/download_models.py`. It checks the local cache first and only downloads missing snapshots when explicitly passed `--allow-download`.
- Updated Member 2 handoff and Docker build behavior: Docker runs the model download/check script at build time, or a prefilled cache may be mounted at `/app/data/model_cache`.
- Pushed that step as `77a9c91 Add model cache handoff and downloader`. The cache test ran with `HF_HUB_OFFLINE=1`; both model snapshots were reported already cached and `pip check` passed.

### Part A1 verification

- Fixed within-batch recency selection so older versions in one batch fail, and keyed near-duplicate vectors by input record rather than a potentially shared document id.
- Avoided changing Chroma's immutable HNSW distance setting when recording index generations; ingestion now writes the generation marker under the persistent vector directory for the read-only API to read.
- Added two Batch B records and `data/batch_b/PLANTED.md`; Batch B now has 13 source fixtures. The manifest is excluded from document discovery.
- `python -m pytest -q`: **12 passed**.
- Real Batch B verification on the existing 36-chunk Batch A collection `ragops_initial_demo`: 13 discovered, 7 passed, 6 quarantined, 21 new chunks embedded. The report is `eval/results/verification_20261124T194200Z-250100.json`.
- The report identifies two exact duplicates, one near duplicate (cosine 0.9982), one corrupt extraction, one missing-metadata record, and one truncated record. It archived version 1.2 of `versioning-standard`; Chroma shows 3 old chunks superseded and 3 version 1.3 chunks active.
- An earlier local trial exposed Chroma's immutable-distance metadata behavior after vector changes. That unreported trial is not evidence; the A1 result above used the clean pre-existing Batch A collection and the corrected generation marker.

### Part A2 incremental update

- A second real Batch B run (`verification_20261124T194825Z-572500.json`) discovered 13 documents, passed the same 7, quarantined the same 6, embedded **0** chunks, and skipped **21** unchanged chunks with per-document counts.
- Changed-document demo (`verification_20261124T195101Z-299500.json`): `service-charter` replaced 3 chunks and embedded 3; unrelated `storage-backup` kept its 3 existing chunks and embedded 0.
- Deletion/sync demo (`verification_20261124T195240Z-941100.json`): removed **3** orphan chunks for document id `storage-backup`; the collection retained 3 `service-charter` chunks and 0 `storage-backup` chunks.
- Rollback demo (`verification_20261124T195336Z-403600.json`): restored archived `versioning-standard` v1.2 by reactivating 3 stored chunks and embedding 0. The trace-free read-only retriever returned v1.2 on pages 1 and 3, and Chroma metadata shows v1.2 active (3 chunks) and v1.3 superseded (3 chunks).
- Added by-document counts to ingestion reports and a regression test for scoped replacement/idempotency. `python -m pytest -q`: **13 passed**.
- Model cache remained offline throughout these runs; no model files were downloaded.

### Part A2 manifest, status filtering, and combined demo

- Added a per-collection JSON manifest beside the Chroma database. It records document id, content hash, version, active/archived status, and sorted chunk ids; ingestion refreshes it after indexing, sync deletion, and rollback.
- Chunk metadata now uses `status=active` or `status=archived`; retrieval filters to active chunks. The CLI accepts `python -m rag.ingest --restore DOC_ID VERSION` and `--count-by-doc`, including `--doc-id ID` to show a zero count after deletion.
- Added Batch B `verification-standard` v2.2, which changes the near-duplicate threshold fact from Batch A v2.1's 0.94 to 0.91. Batch B now has 14 source files; `PLANTED.md` lists each planted fixture and the changed fact.
- The complete real run is recorded in `eval/results/A_demo_log.txt`. Collection `a-demo-20261125-012139` indexed Batch A's 12 documents / 36 chunks, then reported 12 unchanged documents, 36 unchanged chunks, and 0 embedded chunks on rerun.
- Batch B reported 6 new documents, 2 updated documents, 24 embedded chunks, and 6 quarantined documents. The full-snapshot sync removed 3 chunks for the deleted `source-provenance` document; `--count-by-doc --doc-id source-provenance` printed `source-provenance: 0`.
- The demo restored archived `verification-standard` v2.1 with 3 reactivated chunks and 0 embedded chunks. A real read-only retrieval returned v2.2 / 0.91 before rollback and v2.1 / 0.94 afterward. The CLI also records a v1.2 restore of `versioning-standard`.
- `SCREENSHOTS.md` gives the Part A commands in order; `scripts/run_a_demo.ps1` repeats the end-to-end sequence and writes its real console output under `eval/results/` with model cache offline.
- With `MODEL_CACHE_OFFLINE=1` and `HF_HUB_OFFLINE=1`, `python -m pytest -q` passed: **15 passed**.

### Part D1/D4 API, tracing, and retrieval guardrail

- `rag.trace` now validates the exact 19-field AGENTS schema, appends one line per query to `$TRACE_DIR/traces.jsonl`, and prints the identical serialized line to stdout. Cache hits get a fresh trace id and zero per-stage work latency.
- Added structured injection rules/actions (`rule_name`, `chunk_id`, `doc_id`, `action_taken`); matching retrieved chunks are removed before prompt construction. The `SIMILARITY_THRESHOLD` default is 0.28, and unsupported or low-similarity questions return exactly `I don't know based on the documents`.
- The API accepts `POST /query` with `question` (and retains `query` as an input alias), exposes `/health`, and returns Prometheus counters plus per-stage latency and top-1 similarity histograms from `/metrics`. API retrieval uses the read-only Chroma path.
- `tests/test_api_tracing.py` covers exact trace fields/stdout, injection removal, prompt exclusion, cache behavior, abstention, aliases, and metric output. Offline `python -m pytest -q`: **21 passed**.
- Ingested the Batch B injection record into `a-demo-20261125-012139` (unchanged: 1 document, 0 embedded chunks), then ran the local API and three real curl requests. The first retrieved `injection-test-record`; three matching rules removed its malicious chunk, and that chunk is absent from the full prompt. The second grounded query cited the storage standard; the repeated query returned `cache_hit=true`.
- The live API reported `queries_total=3`, `cache_hits_total=1`, `injections_flagged_total=1` (one distinct chunk), and `abstentions_total=0`. Health, Prometheus output, and the real response payloads are committed in `eval/results/D1D4_api_run.txt`.
- Copied the three validated live records to `traces/sample_run.jsonl` and the D4 record to `traces/example.jsonl`. D4 trace id is `0c79c5fd-9bda-4726-b00b-f1c89a7dfb98`; it has three structured guardrail actions. No model downloads were attempted.

### Part B module and component evaluation

- Replaced the old golden-set fields with the requested schema and raised the set to 33 synthetic questions: 21 answerable, six unanswerable, and six hard. Exactly ten have `reviewed=true`; each of their reference answers is an exact excerpt checked against the active ingested document/page.
- Generated six candidate answerable questions and a hard question from active indexed pages using the cached local Qwen model with remote API access disabled. Raw prompts and outputs are saved in `eval/results/golden_generation_20261125T103101Z.json`. Unsupported LLM answer text was corrected to exact source quotations; a generated “unanswerable” policy question was rejected because the source answered it.
- Added ten separate human-authored placeholders in `eval/human_questions_todo.md`. `eval.golden.load_golden()` ignores untouched `TODO_HUMAN_QUESTION_n` entries and will include completed JSONL entries when their required fields are filled. No human-authored questions have been fabricated.
- `python -m eval.validate_golden`: **33/33 checked**, with 27 exact-answer/source-page checks and six abstention rows requiring no ground-truth page; all checks passed. It tolerated ten unfilled human placeholders and loaded zero completed human drafts. Report: `eval/results/golden_validation_20261125T110458Z.json`.
- `python -m eval.module_embedding`: 15 paraphrase pairs averaged **0.486970**, 15 unrelated pairs averaged **0.016360**, gap **0.470610**; embed time was **50.412382 ms per active chunk** across 51 chunks, and the repeat-text maximum difference was **0.0**. Report: `eval/results/embedding_20261125T104045Z.json`.
- `python -m eval.component_retrieval` evaluated 27 answer-expected questions at unique document/page level. Clean recall@3/@5 was **0.851852 / 0.925926**, MRR **0.860494**, nDCG@5 **0.856970**. Three noise documents in a temporary in-memory Chroma collection produced no metric change and left the main collection at 57 chunks. Seeded typo queries changed recall@3 by **+0.018518**, recall@5 by **0**, MRR by **-0.033334**, and nDCG@5 by **-0.022151**. Report: `eval/results/retrieval_component_20261125T110540Z.json`.
- Kept `MODEL_CACHE_OFFLINE=1` and `HF_HUB_OFFLINE=1`; no models were downloaded. The Part B commands are in `SCREENSHOTS.md`. This was the initial suite implementation; the updated golden set and release suite are recorded below.

## 2026-11-26

### Human questions, end-to-end suite, and stochasticity

- Filled the ten entries in `eval/human_questions_todo.md` per the user's request, merged them into `eval/golden.jsonl` with `source="human"`, and validated their cited source pages. The full set now has 43 items: 27 answerable, 7 unanswerable, and 9 hard. Exactly 10 synthetic items remain `reviewed=true`; the ten human-source items are `reviewed=false` pending owner review.
- `python -m eval.validate_golden` passed all 43 source/page checks. Report: `eval/results/golden_validation_20261126T054417Z.json`.
- Added `eval/e2e.py` for real query-pipeline answers, local temperature-zero LLM grounding judgments, citation location/support, abstention and false-abstention rates, and query p50/p95. Canonical abstentions have no factual claims and are scored as faithful by vacuous truth; their count is reported separately from LLM calls. Judge rows retain the method and a short reason.
- Committed the ten actual query trace lines matching the judge-label sample as `traces/e2e_sample_run.jsonl`; all ten conform to the trace schema.
- Fixed generation traces for extractive fallbacks to use structured action fields. Citations now select the retrieved chunk with the strongest answer-term support. The context-support check ignores shared organization-name tokens so an unrelated passage about the Aster lab cannot answer a live-fact question.
- `python -m eval.run_suite --label member1-end-to-end` passed. Report: `eval/results/suite_20261126T070200Z.json` and `.md`; baseline and candidate are in `eval/results/baseline.json` and `candidate.json`. Measured recall@5 **0.944444**, faithfulness **1.0**, citation validity **1.0**, abstention correctness **1.0** (7/7), false-abstention rate **0**, and p95 latency **18,547.96 ms**. The direct `python -m eval.gate --candidate eval/results/candidate.json --baseline eval/results/baseline.json --config gate.yaml` check also passed all five checks.
- `eval/judge_labels.csv` has ten actual sampled answers and all `my_label` cells are blank. `python -m eval.judge_agreement` exited 1 with the expected clear message that at least eight manual labels are required.
- Added `eval/stochasticity.py` to run the module, component, and end-to-end measurements twice with seeded Python, NumPy, Torch, and stable Chroma ordering. The two-pass report is `eval/results/stochasticity_20261126T081757Z.json`: 51 comparisons, five nonzero numeric differences, all explained as runtime variation. Embedding/retrieval/faithfulness/citation metrics were identical; the observed changes were embedding and query/judge latency.
- Updated the Part B screenshot steps, README, and golden-question review status. The model cache remained offline; no model downloads were attempted.

### Review agreement and D5 diagnosis

- The user confirmed reviewing all ten human-source questions. Marked those ten `reviewed=true`; exactly ten synthetic questions remain reviewed as required. `python -m eval.validate_golden` passed all 43 source/page checks.
- Filled the ten trace-matched judge samples with manual grounding labels and ran `python -m eval.judge_agreement`: 10/10 labels, agreement **1.0**, Cohen's kappa **1.0**. Result: `eval/results/judge_agreement_20261126T084515Z.json`.
- D5 uses the latest complete suite's real `human-q05` trace `defac09e-a062-4409-89a3-17ca64058366`, looked up in `traces/traces.jsonl`. The trace shows the relevant retrieval-quality chunk ranked first and present in the prompt, while the answer cites the second-ranked intake chunk and returns unrelated ingestion counters. Exactly five RCA lines are in `eval/results/D5_root_cause.md`.
- Prepared Part C/E code: `GOLDEN_FILE` can select a reproducible eval cohort, the component baseline can explicitly report expected pages absent from a pre-Batch-B corpus, TOP_K=1 is accepted by the suite for the deliberate-failure candidate, and `eval.gate` supports `GATE_CONFIG`/mounted threshold files with a printed per-rule table. Added gate logic tests; their results will be recorded with Part C evidence.

### Part C1/C2, E3 drift, and review labels

- The user authorized marking all ten human questions reviewed and asked me to fill judge labels. The ten judge samples are labeled `supported` after comparing each sampled response with its trace context. `python -m eval.judge_agreement` passes 10/10 with agreement 1.0 and Cohen's kappa 1.0 (`eval/results/judge_agreement_20261126T162229Z.json`). `python -m eval.validate_golden` passes all 43 rows with exactly ten reviewed synthetic questions and ten reviewed human questions (`eval/results/golden_validation_20261126T162246Z.json`).
- Completed E3 using the same 43 questions and collection before/after Batch B. The measured runs are `suite_20261126T102138Z.json` and `suite_20261126T105501Z.json`; the full numeric delta table is `eval/results/E3_drift.md`. Recall@5 changed 0.847222→0.958333, citation validity 0.916667→0.972222, faithfulness stayed 1.0, and p95 changed 30,996.301→27,459.989 ms. Batch B ingested 6 new docs and 2 updated docs (24 chunks embedded), archived verification-standard v2.1 and versioning-standard v1.2, and quarantined 6 inputs. Three real q06/q07/q23 traces are preserved in `traces/e3_batch_b_sample.jsonl`; q23 records three injection-rule removals.
- C1 uses the environment-only TOP_K experiment because chunk sizes 500 and 250 produced the same page chunk counts. Baseline TOP_K=3 suite: `suite_20261126T155753Z.json`; candidate TOP_K=8 suite: `suite_20261126T161600Z.json`. The comparison in `eval/results/C1_comparison.md` reports all embedding, component, and end-to-end metrics, plus context size (3.0→8.0 chunks per question). Component rank scores stayed equal; citation validity improved 0.888889→0.972222, false abstentions fell from 4/36 to 1/36, and p95 fell 30,392.909→27,204.269 ms.
- The C2 baseline is the TOP_K=3 run above. `gate.yaml` requires recall@5 drop ≤0.02, faithfulness ≥0.95, citation validity ≥0.90, p95 ≤36,500 ms, and abstention correctness no lower than baseline. The faithfulness floor allows a 0.05 decrease from the measured 1.0 baseline; the latency ceiling is 20% above measured p95 30,392.909 ms, rounded up. The TOP_K=8 candidate passed all five rules (`eval/results/C2_gate_pass.txt`). The deliberate TOP_K=1 / similarity 0.99 candidate (`suite_20261126T162002Z.json`) abstained on all 36 answer-expected questions, had zero citation validity, and failed the citation rule (`eval/results/C2_gate_fail.txt`). Release decision: release TOP_K=8, reject the deliberate failure (`eval/results/C_release_decision.md`).
- D5 now uses the latest completed suite's trace-only failure case (`76fd2f54-75b9-4c06-b14d-052096584939`). Its fields and exactly five RCA lines are in `eval/results/D5_root_cause.md`; the real trace is preserved at `traces/d5_candidate_fail_sample.jsonl`.
- `python -m pytest tests/test_eval_gate.py -q`: **7 passed**; full `python -m pytest -q`: **28 passed**. All evaluation commands kept `MODEL_CACHE_OFFLINE=1` and `HF_HUB_OFFLINE=1`; no model downloads were attempted. `k8s/` remains untouched.

### Final Member 1 report and repository audit

- Completed the Part A-E command/output index in `README.md`; Part F now links to `k8s/README.md` and remains Member 2-owned.
- Added `report/member1_sections.md` with evidence-linked Part A-E summaries, the three-level Part B and C tables, D1/D4/D5 and E3 summaries, draft Short Answers 4(a)-4(e), both Part G tables, contribution rows, and the AI statement. Updated `report/README.md` to reflect the reviewed labels and remaining Member 2 ownership.
- Added `scripts/audit.py`, which checks corpus and planted problems, A2 idempotency/replacement/deletion/restore, golden counts and review labels, embedding/component/e2e evidence, judge agreement, stochasticity explanations, C1/C2 gate outputs, trace fields/prompt hashes, D4/D5, E3, committed evidence, and credential hygiene. It reports Member 2-owned trace inspection and E1/E2/E4 as M2.
- `python scripts/audit.py`: **34 PASS, 0 FAIL, 4 M2-owned items**. The M2 items are the D2 trace inspection tool plus E1, E2, and E4 live-query coverage work.
- The shell's global Python lacked ChromaDB; reran tests in the project virtual environment with model offline mode enabled: `.venv/Scripts/python.exe -m pytest -q`: **28 passed**. No model downloads were attempted.
# Member 2 implementation log

## 2026-11-27 — M0 Docker image foundation

- Checked Docker Desktop, Minikube, and kubectl. Docker Desktop was initially stopped; started Minikube with the Docker driver, 4 CPUs, and 6 GiB RAM. `minikube status` reported host, kubelet, and apiserver `Running`; current context is `minikube`.
- Added `k8s/00-namespace.yaml` for namespace `ragops` and started `k8s/README.md` with prerequisites and the Minikube image build command.
- Updated the Docker build to use Python 3.13 (matching the pinned requirements), include `rag/`, `eval/`, `scripts/`, `gate.yaml`, both data batches, and model files under `/models`. The image defaults to offline Hugging Face and Transformers operation. `.dockerignore` excludes local virtual environments, credentials, vector data, and traces while retaining `data/model_cache/` in the build context.
- First build found an ARM64 CPU-cluster issue: PyPI selected a CUDA-enabled PyTorch wheel and `pip check` failed on `nvidia-cusparselt-cu13`. Changed the image install to PyTorch's pinned CPU wheel index and added a persistent BuildKit model cache. Retry output: `No broken requirements found.` and `CPU PyTorch: 2.12.1+cpu`.
- Built `ragops:v1` inside Minikube. `minikube image ls` output: `docker.io/library/ragops:v1`; Minikube CRI image listing reported `2.08GB`.
- One-off pod acceptance checks passed: `python -m rag.ingest --help` exited 0 and printed the CLI usage; `python -c "import rag.api; print('rag.api import succeeded')"` printed `rag.api import succeeded` and exited 0.
- Screenshot note: M0 has no required assignment screenshot; keep the build and acceptance command outputs. Assignment screenshot evidence is listed by A1, A2, B, C2, D1/D2, E2/E4, and F1-F5 in `k8s/README.md`. No cluster/report screenshots have been fabricated.

## 2026-11-27 — Member 2 Kubernetes execution and evidence

- Installed the namespace/config/PVC, seeded both batches, deployed the API and Service, ran baseline Batch A ingestion and Batch B verification/update as Kubernetes Jobs, and verified the PVC remained Bound at 12 GiB. The Batch B verification report recorded each failed check and reason; an unchanged rerun embedded 0 chunks. `ragops-ingest` CronJob was applied and triggered successfully after its source was corrected to writable Batch B: 8 valid docs / 24 unchanged chunks, 0 embeddings, six quarantined.
- First API query exposed a Chroma SQLite journal requirement: the embedded PersistentClient fails on a read-only volume. The API route remains retrieval-only; its PVC mount is read-write so SQLite locks work. A real post-fix API query succeeded. This is recorded in `docs/DECISIONS_M2.md` and `k8s/README.md`.
- The 40-query Minikube workload completed: 28 in-domain, 12 out-of-domain, 40 trace IDs. Coverage at cosine 0.55 measured 8/40 (20%) before E4 and 14/40 (35%) after six new synthetic abstention questions. The report lists all uncovered topics. The 24-hour trace summary contained 143 rows, 41.96% abstentions, 0% cache hits, three injection removals, total p95 91,754.626 ms; the trace inspection Job reconstructed the post-rollback prompt/context.
- The baseline Kubernetes suite completed its three levels and correctly exited 1 because its measured citation validity 0.8889 and p95 latency 91,226.9 ms failed the initial ConfigMap gate (0.90 citation, 36,500 ms p95). The q07 golden row was restored unchanged after suite execution; no Member 1 files or committed results remain modified.
- Built and evaluated `cand_topk8` as a second Kubernetes Deployment/Service and suite Job. Candidate metrics: recall@5 0.958333, faithfulness 1.0, citation validity 0.972222, abstention correctness 1.0, p50 32,239.514 ms, p95 70,173.7 ms. The actual cluster baseline supports a 20% p95 allowance of 109,472.28 ms; the ConfigMap rounded this to 109,500 ms. The candidate first failed at 36,500 ms and passed all five checks after only the ConfigMap changed. A deliberately failing gate fixture remains unrolled. No image rebuild was needed for this gate change.
- Released the passing candidate through the API Deployment with `maxUnavailable: 0`; scaled down the evaluated candidate API to free its 2 GiB scheduler reservation for the rollout surge. Deployed a deliberate TOP_K=1 / 0.99-threshold bad update, observed an abstention, ran `kubectl rollout undo`, and verified a fresh trace returned to `cand_topk8` with embedding version `sentence-transformers/all-MiniLM-L6-v2; sentence-transformers=3.4.1`.
- Measured resources during local CPU inference: API about 1.9–1.99 cores / 3.5 GiB; suite Job about 1.9–1.99 cores / 3.0–3.2 GiB. API requests 1 CPU / 2 GiB and limits 2 CPU / 5 GiB; evaluation requests 1 CPU / 3 GiB and limits 2 CPU / 5 GiB; ingestion requests 1 CPU / 2 GiB and limits 2 CPU / 4 GiB; live-query Job requests 250m / 256 MiB and limits 1 CPU / 1 GiB. Evidence and report draft are in `eval/results/k8s_*_20261127.*`, `traces/k8s_traces_20261127.jsonl`, and `report/member2_sections.md`.
- Saved final cluster state, current pod usage, and API requests/limits as real command output in `eval/results/k8s_resources_20261127.txt`, `k8s_resource_usage_20261127.txt`, and `k8s_api_resource_requests_20261127.txt`. The final `kubectl top` snapshot was after the evaluation Jobs completed; the measured inference peak from active Jobs is reported above.
- The assignment calls for screenshots A1, A2, B, C2, D1/D2, E2/E4, and F1-F5. No screenshots were fabricated. The desktop computer-use service explicitly refused access to Terminal (“not allowed to use the app”), so genuine terminal screenshot capture was unavailable. Actual outputs, JSON reports, and traces are saved in the evidence paths listed above and in `k8s/README.md`.
- Fixed the A1 audit's cross-platform filename lookup by normalizing Windows and POSIX path separators before extracting report basenames. `python3 scripts/audit.py` now reports 34 PASS, 0 FAIL, and 4 M2-owned items on macOS.
