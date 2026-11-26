# Golden question review status

`eval/golden.jsonl` contains 43 questions: 27 answerable, seven unanswerable, and nine hard. This includes 33 synthetic questions and ten entries with `source="human"`, filled and merged at the user's request from `eval/human_questions_todo.md`. Exactly ten synthetic entries have `reviewed=true`. The ten `source="human"` entries remain `reviewed=false` until the project owner reviews them; the label records their requested set, not independent human approval.

`python -m eval.validate_golden` checked all 43 answer references and source pages against the selected active collection. The latest validation report is `eval/results/golden_validation_20261126T054417Z.json`. The loader supports unfilled placeholder entries and avoids counting completed entries twice when they are mirrored in the human-question file.

The raw local LLM prompts and candidate outputs used for the synthetic questions are in `eval/results/golden_generation_20261125T103101Z.json`. Unsupported model references were replaced with exact quotations from indexed source pages, and an abstention candidate was rejected when its source answered the question.
