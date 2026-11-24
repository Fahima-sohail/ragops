# Golden question review draft

**Status: pending user approval.** The assignment requires eight group-written questions and eight synthetic questions reviewed by hand. These proposals have not received that approval, so they are marked `pending_user_approval` in `eval/golden.jsonl`. Reply `approved` only after reviewing the wording, answerability, expected evidence, and page labels below. Until then, generated suite outputs are provisional.

The proposed human-authored set is `q01` through `q08`. The proposed synthetic set for human review is `q09` through `q16`. The other questions are synthetic, not reviewed.

| ID | Proposed question | Expected evidence | Proposed answer | Review status |
| --- | --- | --- | --- | --- |
| q01 | What stages handle a query from embedding through answer generation? | service-charter, p. 1 | Embed, retrieve, assemble a bounded prompt, generate a cited answer. | Pending |
| q02 | Which component is permitted to change vectors in the persistent collection? | service-charter, p. 2 | The ingestion writer; the API is read-only. | Pending |
| q03 | List the required fields on an intake record before it is accepted. | intake-standard, p. 1 | Stable id, title, source, date or version, and page count. | Pending |
| q04 | What should happen to chunk embeddings when the same unchanged corpus is ingested again? | intake-standard, p. 3 | No new chunk embeddings should be created. | Pending |
| q05 | Name the kinds of extraction problems that fail the quality check. | verification-standard, p. 1 | Empty text, garbled extraction, or extraction failure. | Pending |
| q06 | At what cosine value is a document treated as a near duplicate? | verification-standard, p. 3 | 0.94. | Pending |
| q07 | How does retrieval handle chunks from an older superseded revision? | versioning-standard, p. 1 | Retain for audit, filter from ordinary retrieval. | Pending |
| q08 | Which four ranking measures are reported by the retrieval evaluation? | retrieval-quality, p. 2 | recall@3, recall@5, MRR, and nDCG@5. | Pending |
| q09 | What should the guardrail do when a retrieved passage asks the model to ignore earlier instructions? | prompt-safety, p. 2 | Withhold it from the prompt and record the action. | Pending |
| q10 | What response is required when the archive lacks evidence for a requested fact? | citations-abstention, p. 2 | Return the standard abstention. | Pending |
| q11 | How many paraphrase pairs and unrelated pairs are required for the embedding check? | evaluation-protocol, p. 2 | At least 15 of each. | Pending |
| q12 | What is the maximum p95 latency set in the release gate document? | release-gate, p. 2 | 30,000 milliseconds for a small local CPU model. | Pending |
| q13 | Which identification and retrieval details must a query trace retain? | trace-observability, p. 1 | Trace id/time, queries, model/collection, retrieved ids, versions, scores, and filters. | Pending |
| q14 | After restoring a prior revision, what must the operator check besides API health? | incident-recovery, p. 2 | A targeted trace showing the expected active version. | Pending |
| q15 | Which process has read-write access to the persistent Chroma directory? | storage-backup, p. 1 | The ingestion job; API is read-only. | Pending |
| q16 | What is the current room temperature in the Aster lab server room? | No supporting document; abstain. | The corpus does not provide enough information to answer this question reliably. | Pending |

Please flag any answer that is ambiguous or unsupported by the cited page. The machine-readable items are in `eval/golden.jsonl`.
