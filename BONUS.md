# Bonus: defects nobody reported

Method: every one of the 43 questions was re-solved independently (hand
arithmetic + the LLM solver in `engine/triage.py --solver`, raw output in
`analysis/llm_solve.json`), including the 4 questions with no reports at all.
The 3 answer-key defects in the data (flux n=1, interference C, LCR 50 V)
were all reported by students — no unreported answer-key defect was found.
What follows is everything else the scan found that no report mentions.

## Unreported, worth fixing

### 1. Solution spelling — Peyer's patches question (61ee6c9d90a1a968a168686b)
The report (R022) was about "plexux" in option D, which is fixed in
`results.json`. The *solution* has two more spelling errors nobody flagged:
"Rugae are **prominant** folds" (prominent) and "**Maceus** membrane of small
intestine" (Mucous membrane). Suggested repair: `spelling` on `solution`,
auto-apply. Low severity, but a student reading the solution learns the
wrong spelling of a word they will write in an exam.

### 2. Solution wording — hormone pairs question (66fe9dbe22132e5a70a3e579)
The report (R035) was about relaxin/inhibin; the key (D) is right. But the
solution says "Insulin and glucagon work **synergistically** to keep blood
glucose concentrations normal" — in a question whose whole point is which
pairs are antagonistic. Insulin and glucagon are antagonistic on blood
glucose (one lowers it, the other raises it); they cooperate to maintain
homeostasis, which is not the same as acting synergistically. A student who
memorises that sentence will get the next antagonism question wrong.
Suggested repair: `solution_fix` on `solution`, faculty review (wording
change in a teaching text). Low severity, key unaffected.

### 3. Solution typo — snake phylogeny question (620e23cecc50543bc7db9186)
The report (R026) was about syllabus; the key (B) is right. The solution
reads "to see it, **wheater**, it has a forked tongue or not" (whether) and
"Forked tongue snakes may **represents** the origin..." Suggested repair:
`spelling` on `solution`, auto-apply. Trivial severity.

### 4. Solution spacing — golden rice question (6264197209f4fd65f58f5707)
The report (R040) was a bare "wrong"; the key (C) is right. The stored
solution itself has words run together in the raw HTML — "Golden **riceis**
genetically engineered to **producebeta-carotene**, a precursor
**ofvitamin** A ... **helpprevent** vitamin A deficiency, which can lead
**tonight** blindness" (to night blindness). Five missing spaces in two
sentences, present in the stored record, not an artefact of extraction.
Suggested repair: `spelling`/`noise` on `solution`, auto-apply.
Low severity, but it reads as a broken page to a student.

## Checked and clean (no reports, no defects found)

| Question | Check |
|---|---|
| Dielectric capacitor (68dea87d387eea3d0d95fbe3) | Charge conservation: V² + V − 30 = 0 → V = 5 V. Key A correct. |
| Two lenses (68dea657387eea3d0d95f54a) | f_eq = 10 cm, P_eq = 10 D, each lens 5 D. Key 5 correct. |
| Dialysis statements (695ede2a88d7701e561aa9d9) | Statement I correct, II incorrect → D. Key correct. |
| Displacement method (68dea6e6387eea3d0d95f6f8) | x = 90 cm, image-size ratio ((150+90)/(150−90))² = 16. Key correct. |

## Negative result, stated plainly
No unreported defect changes any answer key, and no unreported question is
unanswerable. The four items above are all solution-text quality issues.
They are listed here and in the console's "Unreported" tab, not in
`results.json`, because `results.json` is scored per report and inventing
reports would be fabricating data.
