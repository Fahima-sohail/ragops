# Human authored golden questions

Write at least 8 of the 10 questions below by hand. Replace each placeholder's `question`, `type`, `ground_truth_doc`, `ground_truth_page`, `expected_behavior`, and `reference_answer`. Keep `source` as `human`; set `reviewed` to `true` only after you have checked the label against the cited source text. For an unanswerable question, use `type: "unanswerable"`, `expected_behavior: "abstain"`, and null document/page fields. A hard question can use `type: "hard"` and either behavior.

Keep each entry valid JSON in the JSONL block. The evaluation loader ignores entries whose question still starts with `TODO_HUMAN_QUESTION_`; once an entry is complete, it automatically includes it alongside `eval/golden.jsonl` and verifies its source page. Later we can merge completed human rows into the main file when you provide them.

```jsonl
{"id":"human-q01","question":"TODO_HUMAN_QUESTION_1","type":"answerable","source":"human","reviewed":false,"ground_truth_doc":null,"ground_truth_page":null,"expected_behavior":"answer","reference_answer":"TODO_REFERENCE_ANSWER_1"}
{"id":"human-q02","question":"TODO_HUMAN_QUESTION_2","type":"answerable","source":"human","reviewed":false,"ground_truth_doc":null,"ground_truth_page":null,"expected_behavior":"answer","reference_answer":"TODO_REFERENCE_ANSWER_2"}
{"id":"human-q03","question":"TODO_HUMAN_QUESTION_3","type":"answerable","source":"human","reviewed":false,"ground_truth_doc":null,"ground_truth_page":null,"expected_behavior":"answer","reference_answer":"TODO_REFERENCE_ANSWER_3"}
{"id":"human-q04","question":"TODO_HUMAN_QUESTION_4","type":"answerable","source":"human","reviewed":false,"ground_truth_doc":null,"ground_truth_page":null,"expected_behavior":"answer","reference_answer":"TODO_REFERENCE_ANSWER_4"}
{"id":"human-q05","question":"TODO_HUMAN_QUESTION_5","type":"answerable","source":"human","reviewed":false,"ground_truth_doc":null,"ground_truth_page":null,"expected_behavior":"answer","reference_answer":"TODO_REFERENCE_ANSWER_5"}
{"id":"human-q06","question":"TODO_HUMAN_QUESTION_6","type":"answerable","source":"human","reviewed":false,"ground_truth_doc":null,"ground_truth_page":null,"expected_behavior":"answer","reference_answer":"TODO_REFERENCE_ANSWER_6"}
{"id":"human-q07","question":"TODO_HUMAN_QUESTION_7","type":"answerable","source":"human","reviewed":false,"ground_truth_doc":null,"ground_truth_page":null,"expected_behavior":"answer","reference_answer":"TODO_REFERENCE_ANSWER_7"}
{"id":"human-q08","question":"TODO_HUMAN_QUESTION_8","type":"answerable","source":"human","reviewed":false,"ground_truth_doc":null,"ground_truth_page":null,"expected_behavior":"answer","reference_answer":"TODO_REFERENCE_ANSWER_8"}
{"id":"human-q09","question":"TODO_HUMAN_QUESTION_9","type":"answerable","source":"human","reviewed":false,"ground_truth_doc":null,"ground_truth_page":null,"expected_behavior":"answer","reference_answer":"TODO_REFERENCE_ANSWER_9"}
{"id":"human-q10","question":"TODO_HUMAN_QUESTION_10","type":"answerable","source":"human","reviewed":false,"ground_truth_doc":null,"ground_truth_page":null,"expected_behavior":"answer","reference_answer":"TODO_REFERENCE_ANSWER_10"}
```
