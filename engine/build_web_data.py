"""Build the console's data file from the canonical repo data.

web/data.json is a generated snapshot: questions + reports + results.json
grouped into cases, plus the bonus unreported defects from BONUS.md.
Regenerate after any change to results.json:
    python3 engine/build_web_data.py
The console never calls an LLM; it loads this precomputed snapshot.
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SEVERITY = {
    "answer_key": (10, "answer key wrong — every student learns the wrong answer"),
    "option_repair": (9, "question unanswerable as written"),
    "diagram": (9, "question unanswerable as written"),
    "identical_options": (9, "question unanswerable as written"),
    "type_mismatch": (9, "scoring punishes correct answers"),
    "stem_data": (8, "question unsolvable as written"),
    "solution_fix": (7, "key right, teaching wrong"),
    "wrong_chapter": (5, "filed in the wrong chapter"),
    "syllabus": (5, "syllabus question for faculty"),
    "spelling": (3, "cosmetic, but students copy it"),
    "markup_leak": (3, "cosmetic, but students copy it"),
    "exam_reference": (3, "cosmetic, but students copy it"),
    "answer_form": (3, "cosmetic, but students copy it"),
    "noise": (3, "cosmetic, but students copy it"),
}

# Full corrected solution text where the results.json edit is only a
# find/replace pointer (Q23). The console shows this to faculty.
PROPOSED_SOLUTION = {
    "612151a6a34397610a9a2e58": (
        "λ = 0.3 nm = 3.0 Å. K = h²/(2mλ²) = (6.626×10⁻³⁴)² / "
        "(2 × 9.11×10⁻³¹ × (3×10⁻¹⁰)²) = 2.68×10⁻¹⁸ J = 16.7 eV ≈ 16.8 eV (B)."
    )
}

BONUS = [
    {
        "questionId": "61ee6c9d90a1a968a168686b",
        "title": "Solution spelling: 'prominant' and 'Maceus membrane'",
        "detail": "The solution reads 'Rugae are prominant folds' and 'Maceus membrane of small intestine'. Should be 'prominent' and 'Mucous membrane'. Suggested repair: spelling on solution, auto-apply.",
        "severity": "low",
    },
    {
        "questionId": "66fe9dbe22132e5a70a3e579",
        "title": "Solution wording: insulin and glucagon called 'synergistic'",
        "detail": "In a question about which hormone pairs are antagonistic, the solution says insulin and glucagon 'work synergistically'. They are antagonistic on blood glucose. Suggested repair: solution_fix on solution, faculty review.",
        "severity": "low",
    },
    {
        "questionId": "620e23cecc50543bc7db9186",
        "title": "Solution typo: 'wheater' and 'may represents'",
        "detail": "The solution reads 'to see it, wheater, it has a forked tongue' and 'may represents the origin'. Suggested repair: spelling on solution, auto-apply.",
        "severity": "trivial",
    },
    {
        "questionId": "6264197209f4fd65f58f5707",
        "title": "Solution spacing: words run together",
        "detail": "Stored solution has 'Golden riceis', 'producebeta-carotene', 'ofvitamin A', 'helpprevent', 'lead tonight blindness' (to night). Five missing spaces in the stored HTML. Suggested repair: spelling/noise on solution, auto-apply.",
        "severity": "low",
    },
]


def main():
    questions = json.loads((ROOT / "data" / "questions.json").read_text())
    reports = json.loads((ROOT / "data" / "reports.json").read_text())
    results = json.loads((ROOT / "results.json").read_text())
    res_by_report = {r["reportId"]: r for r in results}

    q_out = []
    for q in questions:
        t = q["questionType"]
        b = q[t]
        q_out.append(
            {
                "id": q["_id"],
                "type": t,
                "subject": q.get("subject"),
                "chapter": q.get("chapter"),
                "level": q.get("level"),
                "answer": b.get("answer"),
                "questionHtml": b.get("question", ""),
                "solutionHtml": b.get("solution", ""),
                "proposedSolution": PROPOSED_SOLUTION.get(q["_id"]),
            }
        )

    by_q = defaultdict(list)
    for r in reports:
        by_q[r["questionId"]].append(r)

    cases = []
    for q in questions:
        qid = q["_id"]
        rs = by_q.get(qid, [])
        if not rs:
            continue
        first = res_by_report[rs[0]["reportId"]]
        rep = first["repair"]
        sev, why = SEVERITY.get(rep, (1, "no content change needed")) if rep else (1, "no content change needed")
        if first["verdict"] in ("display_issue", "app_issue", "language_mode"):
            sev, why = 4, "not the question — needs a human/engineering look"
        urgency = len(rs) * sev + (2 if first["verdict"] == "defect" else 0)
        cases.append(
            {
                "questionId": qid,
                "urgency": urgency,
                "urgencyWhy": f"{len(rs)} report(s) · {why}",
                "verdict": first["verdict"],
                "repair": rep,
                "edit": first["edit"],
                "route": first["route"],
                "confidence": first["confidence"],
                "evidence": first["evidence"],
                "reports": [
                    {
                        "reportId": r["reportId"],
                        "comment": r["comment"],
                        "source": r["source"],
                        "reportedAt": r["reportedAt"],
                        "student_reply": res_by_report[r["reportId"]]["student_reply"],
                    }
                    for r in sorted(rs, key=lambda x: x["reportedAt"])
                ],
            }
        )
    cases.sort(key=lambda c: (-c["urgency"], c["questionId"]))

    data = {
        "generated_from": "results.json + data/*.json (see engine/build_web_data.py)",
        "counts": {
            "questions": len(questions),
            "reports": len(reports),
            "cases": len(cases),
            "auto_apply": sum(1 for c in cases if c["route"] == "auto_apply"),
            "faculty_review": sum(1 for c in cases if c["route"] == "faculty_review"),
            "no_change": sum(1 for c in cases if c["route"] == "no_change"),
            "defects": sum(1 for c in cases if c["verdict"] == "defect"),
        },
        "questions": q_out,
        "cases": cases,
        "bonus": BONUS,
        "clean_unreported": [
            {"questionId": "68dea87d387eea3d0d95fbe3", "check": "Charge conservation: V² + V − 30 = 0 → V = 5 V. Key A correct."},
            {"questionId": "68dea657387eea3d0d95f54a", "check": "f_eq = 10 cm, P_eq = 10 D, each lens 5 D. Key 5 correct."},
            {"questionId": "695ede2a88d7701e561aa9d9", "check": "Statement I correct, II incorrect → D. Key correct."},
            {"questionId": "68dea6e6387eea3d0d95f6f8", "check": "x = 90 cm, image-size ratio ((150+90)/(150−90))² = 16. Key correct."},
        ],
    }
    out = ROOT / "web" / "data.json"
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {out}: {data['counts']}")


if __name__ == "__main__":
    main()
