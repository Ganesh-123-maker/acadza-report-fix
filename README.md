# Acadza — Report → Fix

The AI system that sits between a student's "Report error" tap and the fix,
plus the faculty console a tired faculty member would actually want to open
at 10 PM.

Built for the Acadza AI Intern build round (deadline 11 Nov 2026). The
original brief is in `docs/ASSIGNMENT.md`; the data is untouched in `data/`.

## What it does

- **Triage engine** (`engine/`): an independent LLM solver answers each
  question from the question text alone (no key, no solution, no student
  comment), deterministic guards check scope, route, duplicate options,
  missing data and prompt injection, and a human adjudicates every
  disagreement before it lands in `results.json`.
- **Results** (`results.json`): all 44 reports triaged — 26 defects,
  11 no-error, 2 display issues, 1 app issue, 1 language request,
  3 not actionable. 21 reports ready to auto-apply, 9 to faculty review,
  14 no change.
- **Faculty console** (`web/`): queue grouped by question and ordered by
  urgency, questions rendered natively (MathML), verdict + evidence,
  before/after diff, student-reply preview, and approve / edit / reject
  with an audit entry for every action. Loads precomputed results — no
  live LLM calls.
- **Bonus** (`BONUS.md`): 4 defects nobody reported (all solution-text
  quality), and the 4 unreported questions verified clean. No unreported
  defect changes any answer key.

## Run it

```bash
# Triage: validate the adjudicated decisions and regenerate results.json
python3 engine/triage.py

# Also re-run the LLM solver (needs GEMINI_API_KEY) and compare
python3 engine/triage.py --solver

# Rebuild the console data snapshot after changing results.json
python3 engine/build_web_data.py

# Serve the console locally
cd web && python3 -m http.server 8123
# → http://localhost:8123/
```

## Deploy it

The console is a static site; `web/` is the site root (deploy that
directory on Vercel / Netlify / Render). It must stay up for 7 days after
submission. No environment variables, no build step, no server.

## Docs

- `PROMPTS.md` — every product prompt verbatim, prompt version history,
  the prompts given to the coding assistant, 3 moments the AI was wrong
  and how each was caught, and the design decisions log.
- `PRODUCT.md` — who loses most when a question is broken, what the AI
  is never allowed to auto-apply, the week-1 metric, and one idea beyond
  the brief.
- `BONUS.md` — defects nobody reported.
- `SUBMISSION.md` — repo link, live URL, video link, and the 4 submission
  answers (filled in at submission time).

## Repo

https://github.com/Ganesh-123-maker/acadza-report-fix
