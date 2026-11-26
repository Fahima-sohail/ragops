# D5 root-cause analysis

Latest complete suite: `suite_20261126T162002Z` (`cand_topk1`). The single trace record is preserved in `traces/d5_candidate_fail_sample.jsonl`.

## Relevant fields quoted from that trace record

- `trace_id`: `76fd2f54-75b9-4c06-b14d-052096584939`
- `user_query`: `What stages handle a query from embedding through answer generation?`
- `retrieved[0]`: `{"chunk_id":"evaluation-protocol-1.2-0003-fdd27601c010175d","doc_id":"evaluation-protocol","doc_version":"1.2","score":0.426249}`
- `filters`: `{"status":"active","top_k":1,"minimum_similarity":0.99}`
- `response`: `I don't know based on the documents`
- `citations`: `[]`

## Root cause analysis (exactly five lines)

1. The trace shows an active evaluation-protocol chunk scored 0.426249 for the query.
2. The recorded minimum-similarity filter was 0.99, higher than that chunk's score.
3. The trace therefore shows a retrieved match but no evidence eligible under the recorded cutoff.
4. The recorded response is the abstention string and its citations array is empty.
5. Root cause: the configured 0.99 similarity cutoff filtered out the available evidence, causing this answerable query to abstain.
