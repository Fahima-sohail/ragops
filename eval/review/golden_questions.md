# Golden question review status

`eval/golden.jsonl` contains 43 questions: 27 answerable, seven unanswerable, and nine hard. This includes 33 synthetic questions and ten `source="human"` entries filled per the user's request. The user confirmed reviewing all ten human-source questions. Those ten and exactly ten synthetic entries are marked `reviewed=true`; all ground-truth document/page references passed validation against the selected Batch A + Batch B collection.

The current validation output is recorded in `eval/results/golden_validation_20261126T084538Z.json`. The human-source question text and reference answers are also recorded in `eval/human_questions_todo.md`.
