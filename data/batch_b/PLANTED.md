# Batch B planted problems

This manifest describes the fixtures in Batch B. It is not an ingestion document; the discovery stage excludes this file by name.

| Requirement | Fixture | Expected verification outcome |
| --- | --- | --- |
| Exact duplicate 1 | `duplicate-intake.md` | Quarantine: SHA-256 duplicate of the active Document Intake Standard. |
| Exact duplicate 2 | `duplicate-charter.md` | Quarantine: SHA-256 duplicate of the active RAG Service Charter. |
| Near duplicate | `near-duplicate-intake.md` | Quarantine when local embedding cosine similarity reaches the configured 0.94 threshold. |
| Corrupt extraction | `corrupt-extraction.txt` | Quality and uniqueness fail because UTF-8 extraction fails. |
| Truncated source | `truncated-fragment.md` | Completeness fails because the manifest marks the text truncated. |
| Missing metadata | `missing-metadata.md` | Completeness fails for source, date or version, and page count. |
| Newer version | `versioning-standard-v1.3.md` | Pass and supersede/archive active version 1.2 for the same document id. |
| Newer Batch A document version with changed fact | `verification-standard-v2.2.md` | Pass and supersede/archive Batch A version 2.1; near-duplicate threshold changes from 0.94 to 0.91. |
| Prompt injection | `injection-test-record-v1.0.md` | Pass ingestion; the query-time guardrail blocks the planted instruction and records the action. |

Other valid Batch B sources exercise evaluation coverage, latency, document repair, and source provenance. All content is fictional operational test material.
