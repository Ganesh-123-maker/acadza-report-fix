"""Report -> Fix triage engine.

Pipeline (see PROMPTS.md for the full story, including the three times the
LLM was wrong and how each was caught):

  1. SOLVER  — Gemini solves each question from the question text alone.
     No key, no solution, no student comment. (engine/prompts.py: SOLVER_PROMPT)
  2. GUARDS  — deterministic checks on the question text alone:
     duplicate options, numbers the solution uses that the stem never states,
     taxonomy/scope/route validation, and the injection filter that treats
     every student comment as untrusted data.
  3. TRIAGE  — the solver's answer + key + solution + comment go to the
     triage prompt (engine/prompts.py: TRIAGE_PROMPT).
  4. ADJUDICATION — a human reviews every solver/triage disagreement against
     hand arithmetic and the raw MathML. The adjudicated decisions live in
     engine/adjudications.json with a one-line reason each. Nothing reaches
     results.json without passing the guards in engine/guards.py.

Usage:
  python3 engine/triage.py                 # validate adjudications, write results.json
  python3 engine/triage.py --solver        # also run the LLM solver (needs GEMINI_API_KEY)
                                            # writes analysis/llm_solve.json for comparison
The console (web/) loads the precomputed results.json. No live LLM call
happens when a faculty member opens the console — that is deliberate and
cost-aware: triage runs once per report batch, not once per page view.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))

from guards import (  # noqa: E402
    check_decision,
    check_group_consistency,
    duplicate_options,
    load_questions,
    load_reports,
    load_taxonomy,
    missing_values,
    plain_text,
)
from prompts import SOLVER_PROMPT  # noqa: E402


def run_solver(api_key, model="gemini-3.5-flash-lite"):
    """Step 1 only. Batches of 4 questions, temperature 0, JSON mode."""
    import requests

    base = "https://generativelanguage.googleapis.com/v1beta/openai/"
    questions = load_questions()
    reports = load_reports()
    seen, ids = set(), []
    for r in reports:
        if r["questionId"] not in seen:
            seen.add(r["questionId"])
            ids.append(r["questionId"])
    by = {q["_id"]: q for q in questions}
    out = []
    for i in range(0, len(ids), 4):
        batch = []
        for qid in ids[i : i + 4]:
            q = by[qid]
            t = q["questionType"]
            b = q[t]
            batch.append(
                {
                    "qid": qid,
                    "type": t,
                    "subject": q.get("subject"),
                    "chapter": q.get("chapter"),
                    "question_html": b["question"],
                    "solution_html": b.get("solution", ""),
                    "stored_answer": str(b.get("answer")),
                }
            )
        resp = requests.post(
            base + "chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": SOLVER_PROMPT + "\n\n" + json.dumps(batch)}],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            },
            timeout=120,
        )
        resp.raise_for_status()
        txt = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(txt)
        out.extend(data if isinstance(data, list) else data.get("results", []))
    return out


def build_results(verbose=False):
    taxonomy = load_taxonomy()
    questions = load_questions()
    reports = load_reports()
    q_by_id = {q["_id"]: q for q in questions}
    r_by_id = {r["reportId"]: r for r in reports}
    decisions = json.loads((ROOT / "engine" / "adjudications.json").read_text())["decisions"]

    errors = []
    if len(decisions) != len(reports):
        errors.append(f"{len(decisions)} decisions for {len(reports)} reports")
    seen = {d["reportId"] for d in decisions}
    if seen != set(r_by_id):
        errors.append(f"reportId mismatch: missing {set(r_by_id)-seen}, extra {seen-set(r_by_id)}")
    for d in decisions:
        errors += [f"{d['reportId']}: {e}" for e in check_decision(d, taxonomy, q_by_id, r_by_id)]
        # decision must point at the report's own question
        if r_by_id.get(d["reportId"], {}).get("questionId") != d["questionId"]:
            errors.append(f"{d['reportId']}: questionId does not match the report")
    errors += check_group_consistency(decisions)

    # Deterministic scans, reported only with --verbose: the LLM solver missed
    # duplicate options and missing-data defects, and these scans catch them
    # — but the missing-value scan over-flags (see guards.missing_values),
    # so both are review aids, never auto-verdicts.
    if verbose:
        for q in questions:
            t = q["questionType"]
            b = q[t]
            dup = duplicate_options(b["question"])
            if dup:
                print(f"scan: {q['_id']} duplicate options {dup[0]}/{dup[1]} = {dup[2]!r}")
            mv = missing_values(b["question"], b.get("solution", ""))
            if mv:
                print(f"scan: {q['_id']} solution uses numbers absent from stem: {mv}")

    if errors:
        print("GUARD FAILURES:")
        for e in errors:
            print(" -", e)
        sys.exit(1)

    results = [
        {
            "reportId": d["reportId"],
            "questionId": d["questionId"],
            "verdict": d["verdict"],
            "repair": d["repair"],
            "edit": d["edit"],
            "route": d["route"],
            "confidence": d["confidence"],
            "evidence": d["evidence"],
            "student_reply": d["student_reply"],
        }
        for d in sorted(decisions, key=lambda x: x["reportId"])
    ]
    out = ROOT / "results.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    from collections import Counter

    print(f"wrote {out} ({len(results)} reports)")
    print("verdicts:", dict(Counter(r["verdict"] for r in results)))
    print("routes:", dict(Counter(r["route"] for r in results)))
    print("repairs:", dict(Counter(str(r["repair"]) for r in results if r["repair"])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solver", action="store_true", help="run the LLM solver first")
    ap.add_argument("--verbose", action="store_true", help="print deterministic scan output")
    args = ap.parse_args()
    if args.solver:
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not key:
            print("set GEMINI_API_KEY (Gemini OpenAI-compatible endpoint) and retry")
            sys.exit(2)
        raw = run_solver(key)
        dest = ROOT / "analysis" / "llm_solve.json"
        dest.parent.mkdir(exist_ok=True)
        dest.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {dest} ({len(raw)} solver rows)")
    build_results(verbose=args.verbose)


if __name__ == "__main__":
    main()
