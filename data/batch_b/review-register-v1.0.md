---
doc_id: review-register
source: Aster Research Lab policy archive (fictional test corpus)
title: Human Review Register
version: 1.0
date: 2026-11-12
page_count: 3
---

## Page 1

A reviewer checks the wording, answerability, source id, page number, and expected behavior for each proposed golden question. A second reviewer checks a sample of synthetic questions and records whether the judge agrees with the human faithfulness label. The review record names the question id and status without storing personal data.

## Page 2

Draft labels are not final labels. A question that has not been reviewed is reported as pending and excluded from any claim that the assignment's human-review requirement is complete. Reviewers may correct the expected source or mark a question ambiguous. The evaluation result retains the draft status so a reader can distinguish a pipeline run from an approved dataset.

## Page 3

The final review response is recorded in the repository with the date and scope of approval. After approval, the golden JSONL and judge comparison file receive final review labels, and the suite runs again. A change to question wording or expected source reopens review for that item.
