# Member 1 report sections — CS4032 Assignment 03

This is a draft of Member 1's report material. The corpus is a fictional Aster Research Lab scenario. Every measured value below comes from the named committed result or trace file; Part E live-query coverage and Part F cluster results remain Member 2 evidence.

## Part A — Data quality, updates, and rollback

Batch B's committed verification run discovered 14 source fixtures, passed 8, quarantined 6, and embedded 24 chunks. The two updated documents superseded and archived the earlier versions. The injection document was intentionally allowed through document intake so the query-time rail could be tested.

| Planted problem | Verification result | What detected it / disposition |
| --- | --- | --- |
| Exact duplicate: `duplicate-intake.md` | Quarantined | Uniqueness failed: SHA-256 duplicate of `intake-standard`. |
| Exact duplicate: `duplicate-charter.md` | Quarantined | Uniqueness failed: SHA-256 duplicate of `service-charter`. |
| Near duplicate: `near-duplicate-intake.md` | Quarantined | Uniqueness failed at cosine 0.9982 against a 0.94 threshold. |
| Corrupt extraction: `corrupt-extraction.txt` | Quarantined | Quality failed on UTF-8 extraction; completeness also failed because metadata could not be parsed. |
| Truncated record: `truncated-fragment.md` | Quarantined | Completeness failed: marked truncated and declared page count differed from extracted count. |
| Missing metadata: `missing-metadata.md` | Quarantined | Completeness failed for source, version/date, and page count. |
| Newer verification standard v2.2 | Passed; v2.1 archived | Recency recognized the newer version. It changes the near-duplicate threshold from 0.94 to 0.91. |
| Newer versioning standard v1.3 | Passed; v1.2 archived | Recency recognized the newer version; archived content remains available for restore. |
| Injected instruction: `injection-test-record-v1.0.md` | Passed intake | This was the intake check's deliberate miss: the document was complete and unique. D4's retrieval guardrail removed the retrieved chunk before prompt construction. |

The highest detection count is a tie: **uniqueness rejected three duplicate fixtures**, while **completeness rejected three fixtures** (the corrupt record, truncated record, and missing-metadata record). The injected instruction is not a metadata or duplicate defect, so the retrieval guardrail is the relevant defense. The A2 run also recorded zero embeddings on an unchanged rerun, scoped replacement of the changed document, zero remaining chunks for the deleted document, and a restore with reactivated archived chunks and no embedding.

Evidence for the table and counts: `eval/results/verification_20261126T102215Z-326500.json`. A2 console sequence and deletion count: `eval/results/A_demo_log.txt`; supporting incremental reports: `verification_20261124T194825Z-572500.json`, `verification_20261124T195101Z-299500.json`, `verification_20261124T195240Z-941100.json`, and `verification_20261124T195336Z-403600.json` in `eval/results/`.

## Part B — Offline evaluation

The set contains 43 questions: 27 answerable, 7 unanswerable, and 9 hard; its 36 answer-expected items include the 9 hard questions. There are 33 synthetic questions and 10 human questions. Ten synthetic questions and ten user-reviewed human questions are marked reviewed.

| Evaluation level | Result | Reading |
| --- | --- | --- |
| Golden set | 43 total; 27 answerable, 7 unanswerable, 9 hard; 33 synthetic, 10 human; 10 reviewed synthetic | Meets the set-size and category requirements. The answer-expected count used by component and end-to-end metrics is 36 because it includes hard answerable questions. |
| Embedding module | 15 paraphrase pairs; mean cosine 0.486970. 15 unrelated pairs; mean cosine 0.016360. Gap 0.470610. Determinism maximum difference 0.0. | The encoder separates the sampled paraphrase and unrelated pairs, but this module result does not guarantee retrieval or answer quality. |
| Component retrieval, clean | Recall@3 0.861111; recall@5 0.958333; MRR 0.832870; nDCG@5 0.853492. | Document/page retrieval on the 36 answer-expected questions. |
| Component retrieval, 3 noise documents | Same four metrics as clean; main collection unchanged. | Irrelevant documents in the temporary collection did not measurably alter this run. |
| Component retrieval, typo queries | Recall@3 0.791667; recall@5 0.875000; MRR 0.743981; nDCG@5 0.764725. | Seeded character transpositions reduced retrieval scores. |
| End-to-end | Faithfulness 1.000000; abstention correctness 1.000000 (7/7); false-abstention rate 0.111111 (4/36); citation validity 0.888889 (32/36); p50 12,132.882 ms; p95 30,392.909 ms. | A perfect faithfulness score did not mean every answer was useful: the run still falsely abstained four times and had four invalid or missing citations among answer-expected questions. |

Evidence for golden-set, embedding, component, and end-to-end rows: `eval/results/suite_20261126T155753Z.json` (43-question dataset, baseline TOP_K=3). The standalone pair definition is `eval/embedding_pairs.json`. The noise test uses three irrelevant documents in a temporary collection and records that the main collection was unchanged in the suite JSON.

| Additional Part B check | Result | Evidence |
| --- | --- | --- |
| Judge agreement | 10 labeled answers; agreement 1.000000; Cohen's kappa 1.000000. | `eval/results/judge_agreement_20261126T162229Z.json` |
| Stochasticity | Two seeded suite passes; five runtime measurements differed and each nonzero difference has an explanation. | `eval/results/stochasticity_20261126T081757Z.json` |

The module/component contrast is useful: the embedding gap was 0.470610 and clean recall@5 was 0.958333, while the same end-to-end run still had a 0.111111 false-abstention rate and citation validity of 0.888889. Similarity and retrieval metrics alone do not score whether the generated answer addresses the question or cites its support.

## Part C — Candidate comparison and release decision

The candidate changes only the configured retrieval cap: TOP_K=3 to TOP_K=8. The embedding and component-ranking metrics remained the same because the collection and evaluation corpus did not change; end-to-end generation received more retrieved context.

| Level / metric | Baseline TOP_K=3 | Candidate TOP_K=8 | Delta |
| --- | ---: | ---: | ---: |
| Embedding similarity gap | 0.470610 | 0.470610 | 0 |
| Embedding time per chunk (ms) | 39.752011 | 33.942552 | -5.809459 |
| Component recall@5 | 0.958333 | 0.958333 | 0 |
| Component MRR | 0.832870 | 0.832870 | 0 |
| End-to-end citation validity | 0.888889 | 0.972222 | +0.083333 |
| End-to-end false-abstention rate | 0.111111 | 0.027778 | -0.083333 |
| End-to-end faithfulness | 1.000000 | 1.000000 | 0 |
| End-to-end abstention correctness | 1.000000 | 1.000000 | 0 |
| End-to-end p95 latency (ms) | 30,392.909 | 27,204.269 | -3,188.640 |

Evidence: `eval/results/suite_20261126T155753Z.json`, `eval/results/suite_20261126T161600Z.json`, and the three-level delta table in `eval/results/C1_comparison.md`.

**Release decision: release TOP_K=8; reject TOP_K=1 with similarity threshold 0.99.** The passing run met all five gate rules, including recall@5 drop 0.000000 (maximum 0.020000), faithfulness 1.000000 (minimum 0.950000), citation validity 0.972222 (minimum 0.900000), p95 27,204.269 ms (maximum 36,500 ms), and abstention correctness equal to baseline at 1.000000. The deliberate failing candidate had citation validity 0 and falsely abstained on all 36 answer-expected questions; it failed the citation rule despite its low latency. Evidence: `eval/results/C2_gate_pass.txt`, `eval/results/C2_gate_fail.txt`, and `eval/results/C_release_decision.md`.

## Part D — D1, D4, and D5

| Item | Observed result | Evidence |
| --- | --- | --- |
| D1 API and metrics | Health endpoint returned `status=ok`; three query requests produced `queries_total=3`, `cache_hits_total=1`, `injections_flagged_total=1`, and `abstentions_total=0`. Per-stage latency histograms and top-1 similarity are included in the Prometheus output. | `eval/results/D1D4_api_run.txt` |
| D4 retrieval rail | The injected retrieved chunk was removed by three matching rules: `ignore_previous_instructions`, `reveal_system_prompt`, and `api_key_exfiltration`. The actions record chunk and document ids. | `traces/example.jsonl`; the same real API session is in `eval/results/D1D4_api_run.txt` |
| D5 root cause | Trace `76fd2f54-75b9-4c06-b14d-052096584939` records the top retrieved chunk at score 0.426249 and a minimum-similarity filter of 0.99; the answer abstained with no citations. The five-line analysis identifies the threshold as the cause. | `traces/d5_candidate_fail_sample.jsonl` and `eval/results/D5_root_cause.md` |

The D5 diagnosis is based on fields from the trace record. The trace is from the deliberate failing candidate, so it demonstrates why a speed-only comparison would be misleading.

## Part E — E3 Batch B drift

| Metric | Before Batch B | After Batch B | Change |
| --- | ---: | ---: | ---: |
| Clean component recall@5 | 0.847222 | 0.958333 | +0.111111 |
| Clean component MRR | 0.756944 | 0.832870 | +0.075926 |
| Clean component nDCG@5 | 0.772112 | 0.853492 | +0.081380 |
| End-to-end citation validity | 0.916667 | 0.972222 | +0.055555 |
| End-to-end faithfulness | 1.000000 | 1.000000 | 0 |
| False-abstention rate | 0.083333 | 0.027778 | -0.055555 |
| p95 latency (ms) | 30,996.301 | 27,459.989 | -3,536.312 |

Evidence: the full before/after metric table is `eval/results/E3_drift.md`; raw runs are `eval/results/suite_20261126T102138Z.json` and `eval/results/suite_20261126T105501Z.json`.

Batch B added six new documents, updated two existing documents, embedded 24 chunks, and quarantined six planted duplicate/invalid fixtures. The newer verification standard changed the near-duplicate threshold; the previous verification and versioning documents were archived and the active-version filter excludes their old chunks. The injected document passed ingestion, then the q23 trace records its chunk being removed before the prompt. These corpus changes explain improved retrieval coverage and citations. They do not make every answer relevant: the q23 trace shows a context-supported response that does not directly answer the question. Evidence: `eval/results/verification_20261126T102215Z-326500.json`, `eval/results/E3_drift.md`, and `traces/e3_batch_b_sample.jsonl`.

## Part G — Draft report tables and short answers

### Table 1 — Figure 3 stages

| Stage | What this project does | File / evidence | Missing or remaining work |
| --- | --- | --- | --- |
| Ingest | Parse documents, chunk and hash content, embed and persist vectors, and keep a document/version/chunk manifest. | `rag/ingest.py`, `rag/store.py`, A2 reports in `eval/results/` | PVC and scheduled Kubernetes Job: [M2]. |
| Verify | Check quality, completeness, recency, and uniqueness; quarantine failures; save each run report. | `rag/verify.py`, `data/batch_b/PLANTED.md`, `eval/results/verification_20261126T102215Z-326500.json` | Current demonstration fixtures are Markdown/text; production PDF extraction needs corpus-specific validation. |
| Update data lake | Preserve rejected inputs in quarantine and superseded source versions in archive; restore an archived version on request. | `data/quarantine/`, `data/archive/`, `rag/ingest.py`, `eval/results/A_demo_log.txt` | Persistent Kubernetes mounts: [M2]. |
| Update retrieval sources | Keep chunk status metadata, filter archived chunks, and expose Chroma to the API read-only; ingestion is the writer. | `rag/store.py`, `rag/retrieve.py`, `rag/api.py`, `docs/HANDOFF_MEMBER2.md` | Enforce read-only API mount and ingestion Job write access in cluster: [M2]. |
| Offline testing | Run embedding, clean/noise/typo retrieval, end-to-end, judge agreement, stochasticity, and the release gate. | `eval/run_suite.py`, `eval/module_embedding.py`, `eval/component_retrieval.py`, `eval/e2e.py`, `eval/results/` | No missing Member 1 offline evidence identified. |
| Live testing | Run the local API, capture real request traces, and expose health/Prometheus metrics. | `rag/api.py`, `eval/results/D1D4_api_run.txt`, `traces/sample_run.jsonl` | At least 40 live-query fixtures and cluster service run: [M2]. |
| Check coverage | Compare live queries to golden questions, group gaps, add questions, and enforce a coverage threshold. | Member 2 coverage implementation | Coverage script, threshold report, and six-question before/after evidence: [M2]. |

### Table 2 — Quality attributes

| Quality | What we measure | Threshold | Evidence |
| --- | --- | --- | --- |
| Adaptability | Recall@5 change for a configurable candidate pipeline. | Candidate drop no more than 0.02 against baseline. | `gate.yaml`, `eval/results/C2_gate_pass.txt` |
| Monitorability | Query counters, cache hits, injection flags, abstentions, stage latency histograms, top-1 similarity; suite p95. | p95 at most 36,500 ms for this local release gate. Kubernetes resource and availability thresholds: [M2]. | `eval/results/D1D4_api_run.txt`, `eval/results/C2_gate_pass.txt` |
| Observability | Required trace fields, prompt hash/full prompt, retrieved document versions, citations, guardrail actions, and stage latency. | Every sampled query trace must contain the complete schema and matching prompt hash. | `traces/example.jsonl`, `traces/e3_batch_b_sample.jsonl` |
| Traceability | UUID trace id connects query, filter, chunk/document version, prompt, response, and citations. | One trace record per query; trace-only D5 diagnosis must locate the cause. | `traces/d5_candidate_fail_sample.jsonl`, `eval/results/D5_root_cause.md` |
| Reliability | Abstention correctness, citation validity, and injection removal. | Abstention correctness no lower than baseline; passing candidate must meet citation gate 0.90; injected chunk removed before prompt. | `eval/results/C2_gate_pass.txt`, `eval/results/D1D4_api_run.txt`, `traces/example.jsonl` |

### Short answers 4(a)–4(e)

**4(a) Which verification check caught the most problems, and what was missed?** Uniqueness and completeness tied: each rejected three planted fixtures. Uniqueness caught two exact duplicates and one near-duplicate; completeness caught the corrupt record, truncated record, and missing metadata. The instruction injection passed intake. The query-time retrieval guardrail caught it and removed its chunk before prompting. Evidence: `eval/results/verification_20261126T102215Z-326500.json` and `traces/example.jsonl`.

**4(b) Did a module metric look fine while a component or end-to-end metric did not?** Yes. The embedding module measured a 0.470610 paraphrase/unrelated gap and deterministic repeat embeddings, but the baseline end-to-end run still had a 0.111111 false-abstention rate and 0.888889 citation validity. A good embedding separation score does not establish that the right page is retrieved, the question is answered, or citations are valid. Evidence: `eval/results/suite_20261126T155753Z.json`.

**4(c) Archive or delete old versions? What breaks if deleted?** We archive superseded source documents and mark their old chunks archived so retrieval filters them out; restore reactivates old chunks without re-embedding. Deleting the old copy would remove rollback and historical comparison evidence and could leave the manifest unable to restore the prior version. Evidence: `eval/results/A_demo_log.txt` and `verification_20261126T102215Z-326500.json`.

**4(d) Which metric is least trusted, and why?** I trust aggregate faithfulness least when read alone. The suite assigns canonical abstentions a vacuous-truth faithfulness score, and the q23 trace has a supported response that still misses the question. Faithfulness must be read beside answer relevance, false abstentions, citations, and the actual trace. Evidence: `eval/results/E3_drift.md` and `traces/e3_batch_b_sample.jsonl`.

**4(e) What was hardest from the paper, and what changed?** The hardest idea was treating data management and model/query evaluation as one lifecycle rather than tuning the LLM alone. The paper frames RAG operations around both LLM and data lifecycles ([Xu et al., arXiv:2506.03401](https://arxiv.org/abs/2506.03401)). We made that concrete with document hashes and versions, quarantine/archive and restore, active-version retrieval filtering, and before/after drift suites. Live-query coverage and cluster operation remain Member 2 work.

### Contribution table

| Member | Contribution |
| --- | --- |
| Member 1 | Implemented ingestion, verification, persistent vector-store manifest and retrieval, generator/guardrail, API and traces, Parts A–D evaluation and gates, Batch A/B fixtures, evidence reports, and this Member 1 report draft. Ran the documented local checks and evaluation commands. |
| Member 2 | Owns `k8s/`, Dockerfile, live-query and coverage scripts, metrics summary, trace inspection tool, Kubernetes runs/screenshots, and Part F evidence. |

### AI statement

Codex was used for code generation and to help draft these report sections. I reviewed the questions, labels, code, traces, and results, and I ran the documented commands and tests. I take responsibility for the final submission and demo.
