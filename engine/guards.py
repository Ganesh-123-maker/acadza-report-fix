"""Deterministic guards. These run on every triage output before it can
become a result. No LLM output reaches results.json without passing them.
They exist because the LLM alone was observed to fail on exactly these points
(see PROMPTS.md, '3 moments where the AI was wrong').
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_taxonomy():
    return json.loads((ROOT / "data" / "taxonomy.json").read_text())


def load_questions():
    return json.loads((ROOT / "data" / "questions.json").read_text())


def load_reports():
    return json.loads((ROOT / "data" / "reports.json").read_text())


# ---------------------------------------------------------------- text
def plain_text(html: str) -> str:
    """MathML-aware flattening of stored HTML.

    A naive tag-strip once made cos(45deg) = 1/sqrt(2) look like 1/2 and made
    a correct solution look self-contradictory (Q40). Fractions and roots are
    therefore rendered explicitly instead of being dropped.
    """
    if not html:
        return ""
    s = html
    s = re.sub(r"<br\s*/?>", " | ", s, flags=re.I)
    # mfrac with two <mrow> children -> (num)/(den), applied repeatedly so
    # nested fractions resolve inside-out. This is the Q40 lesson: a naive
    # strip turned 1/sqrt(2) into "1 2", which reads as 1/2.
    for _ in range(5):
        s2 = re.sub(
            r"<mfrac[^>]*>\s*<mrow[^>]*>(.*?)</mrow>\s*<mrow[^>]*>(.*?)</mrow>\s*</mfrac>",
            lambda m: "(" + m.group(1) + ")/(" + m.group(2) + ")",
            s,
            flags=re.S,
        )
        if s2 == s:
            break
        s = s2
    s = re.sub(r"<mfrac[^>]*>", "(", s)
    s = re.sub(r"</mfrac>", ")", s)
    s = re.sub(r"<msqrt[^>]*>", "sqrt(", s)
    s = re.sub(r"</msqrt>", ")", s)
    s = re.sub(r"<[^>]+>", " ", s)
    import html as _html

    s = _html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------- guards
_INSTRUCTION_LIKE = re.compile(
    r"(ignore|disregard|forget|override|you are (now|the)|change the answer|"
    r"mark this|previous instructions|system prompt|admin)",
    re.I,
)


def comment_is_instruction_like(comment: str) -> bool:
    """The student comment is untrusted data. If it reads like an instruction
    to the system rather than a report about the question, it must never drive
    an edit. The triage may still act on a defect the independent solver
    proves — but never because the comment said to."""
    return bool(_INSTRUCTION_LIKE.search(comment or ""))


def check_decision(dec, taxonomy, questions_by_id, reports_by_id):
    """Return a list of guard violations for one adjudicated decision."""
    errors = []
    verdicts = taxonomy["verdicts"]
    repairs = taxonomy["repairs"]
    if dec["verdict"] not in verdicts:
        errors.append(f"unknown verdict {dec['verdict']!r}")
    rep = dec.get("repair")
    if dec["verdict"] == "defect":
        if rep not in repairs:
            errors.append("defect without a valid repair")
    else:
        if rep is not None:
            errors.append(f"non-defect verdict {dec['verdict']} must have repair null")
    edit = dec.get("edit")
    if rep is not None and edit is not None:
        allowed = repairs[rep]["fields"]
        if edit["field"] not in allowed:
            errors.append(
                f"edit field {edit['field']!r} outside repair {rep} scope {allowed}"
            )
        if not repairs[rep]["auto"]:
            errors.append(f"repair {rep} is auto:false but an edit was proposed")
    if rep is not None and not repairs[rep]["auto"] and edit is not None:
        errors.append("auto:false repair must not carry an edit")
    # route rules
    route = dec["route"]
    if dec["verdict"] == "defect" and rep is not None:
        if repairs[rep]["auto"] and dec["confidence"] >= 0.85:
            want = "auto_apply"
        else:
            want = "faculty_review"
        if route != want:
            errors.append(f"route {route} but rules give {want}")
    elif dec["verdict"] in ("display_issue", "app_issue", "language_mode"):
        if route != "faculty_review":
            errors.append(f"{dec['verdict']} must route faculty_review")
    elif dec["verdict"] in ("no_error", "not_actionable", "already_fixed"):
        if route != "no_change":
            errors.append(f"{dec['verdict']} must route no_change")
    if not (0.0 <= dec["confidence"] <= 1.0):
        errors.append("confidence outside [0, 1]")
    # student reply: 1-3 sentences
    n_sent = len([p for p in re.split(r"[.!?]\s+", dec["student_reply"].strip()) if p])
    if not (1 <= n_sent <= 3):
        errors.append(f"student_reply has {n_sent} sentences, must be 1-3")
    # injection guard: an instruction-like comment must never produce an edit
    # on its own. (R027: the comment tried; the decision is not_actionable.)
    rep_obj = reports_by_id.get(dec["reportId"])
    if rep_obj and comment_is_instruction_like(rep_obj["comment"]) and edit is not None:
        errors.append("instruction-like comment produced an edit — refused")
    if dec["questionId"] not in questions_by_id:
        errors.append("unknown questionId")
    return errors


def check_group_consistency(decisions):
    """Reports on the same question must agree on verdict/repair/edit.
    They are the same defect (or the same non-defect), seen by several
    students; letting one student's wording change the verdict would be
    grading the student, not the question."""
    errors = []
    by_q = {}
    for d in decisions:
        by_q.setdefault(d["questionId"], []).append(d)
    for qid, ds in by_q.items():
        keys = {(d["verdict"], d["repair"], json.dumps(d["edit"], sort_keys=True)) for d in ds}
        if len(keys) > 1:
            errors.append(f"{qid}: reports disagree: {sorted(keys)}")
    return errors


def duplicate_options(question_html: str):
    """Deterministic scan the LLM missed: two options with identical text."""
    text = plain_text(question_html)
    opts = re.findall(r"\(([A-D])\)\s*([^|(]+?)(?=\s*\|?\s*\([A-D]\)|\s*$)", text)
    seen = {}
    for letter, val in opts:
        v = val.strip()
        if v in seen:
            return (seen[v], letter, v)
        seen[v] = letter
    return None


def missing_values(question_html: str, solution_text: str):
    """Recall-first review aid, NOT a verdict: numbers the solution uses that
    the question never states. It deliberately over-flags — derived numbers
    (50 V, 311.3, ...) look exactly like missing inputs to a regex — so it
    is shown to the human adjudicator and never auto-routes. On this dataset
    it flags 29/43 questions; the two real stem_data defects (Q7's 10 cm
    side, Q24's 95.5 mH) are inside that list, which is the point: high
    recall, human precision. See PROMPTS.md."""
    qnums = set(re.findall(r"\d+(?:\.\d+)?", plain_text(question_html)))
    snums = set(re.findall(r"\d+(?:\.\d+)?", plain_text(solution_text)))
    return sorted(snums - qnums)
