---
doc_id: feedback-loop
source: Aster Research Lab policy archive (fictional test corpus)
title: Evaluation Feedback Loop
version: 1.0
date: 2026-11-12
page_count: 3
---

## Page 1

Operators group uncovered user questions by topic before changing the golden set. A new question states its answerability, expected source, and page. A question is not added merely because one model answered it incorrectly; the owner first checks whether the source archive contains the requested evidence.

## Page 2

Coverage compares live queries with the closest golden question using the same embedding model. The selected threshold is documented with the run. The uncovered list includes the query, its closest score, and a short topic label. A coverage failure exits non-zero so a scheduled check can alert the owner.

## Page 3

After approved questions are added, the full offline suite runs again and writes a timestamped result. The report compares the old and expanded coverage, retrieval metrics, abstention behavior, and gate decision. Synthetic questions are reviewed for ambiguity and for whether their labels match the source page.
