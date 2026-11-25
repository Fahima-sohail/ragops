# Golden question review status

`eval/golden.jsonl` currently contains 33 synthetic items: 21 answerable, six unanswerable, and six hard. Exactly ten synthetic entries have `reviewed=true` after their wording, reference answer, and source page were checked against active indexed text. The code-generated checks are recorded in `eval/results/golden_validation_20261125T110458Z.json`.

No human-authored questions have been added to the machine-readable golden set. Ten blank entries are in `eval/human_questions_todo.md`; the loader ignores untouched placeholders and picks up completed entries after the user supplies the question and labels. Human review is still pending, so end-to-end suite results remain provisional until at least eight hand-written questions are supplied and reviewed.

The raw local LLM prompts and candidate outputs used for the new synthetic questions are in `eval/results/golden_generation_20261125T103101Z.json`. Unsupported model references were replaced with exact quotations from the indexed source pages, and one generated abstention candidate was rejected because the source itself answered it. The accepted hard question is included in `eval/golden.jsonl`; the absent-personal-fact abstention entry was written separately after rejecting the model's answerable policy question.
