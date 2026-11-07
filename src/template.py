"""Blank questionnaire and reader for the assessment answers.

The questionnaire is inputs/assessment_<property>.csv with four columns:
control_id, maturity, evidence_ref and comment. Maturity is a whole number from 0 to 4
(0 not in place, 1 ad hoc, 2 documented, 3 implemented with evidence, 4 measured and reviewed).
A blank maturity means the control was not answered. Only applicable controls are listed.
A second file, assessment_<property>_questions.csv, lists the question and the expected evidence
for each control so the person answering does not need the catalogue open.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MAX_MATURITY, read_csv, write_csv  # noqa: E402

TEMPLATE_FIELDS = ["control_id", "maturity", "evidence_ref", "comment"]
GUIDE_FIELDS = ["control_id", "domain", "title", "level", "assessment_question", "evidence_expected", "accountable"]


def template_rows(applicability_rows):
    """One blank row per applicable control."""
    return [{"control_id": r["control_id"], "maturity": "", "evidence_ref": "", "comment": ""}
            for r in applicability_rows if r["applicable"] == "yes"]


def guide_rows(controls_by_id, applicability_rows):
    rows = []
    for r in applicability_rows:
        if r["applicable"] != "yes":
            continue
        c = controls_by_id[r["control_id"]]
        rows.append({"control_id": c["control_id"], "domain": c["domain"], "title": c["title"], "level": c["level"],
                     "assessment_question": c["assessment_question"], "evidence_expected": c["evidence_expected"],
                     "accountable": r["accountable"]})
    return rows


def write_template(path, controls_by_id, applicability_rows):
    """Write the blank questionnaire and its question guide. Returns both paths."""
    write_csv(path, template_rows(applicability_rows), TEMPLATE_FIELDS)
    guide_path = os.path.splitext(path)[0] + "_questions.csv"
    write_csv(guide_path, guide_rows(controls_by_id, applicability_rows), GUIDE_FIELDS)
    return path, guide_path


def parse_assessment(rows, controls_by_id, applicable_ids):
    """Turn questionnaire rows into answers.

    Returns (answers, problems). answers maps control_id to {"maturity": int or None, "evidence_ref", "comment"}.
    Problems are plain sentences. Rows for unknown or inapplicable controls are ignored and reported.
    """
    answers, problems = {}, []
    applicable = set(applicable_ids)
    for n, r in enumerate(rows, 2):
        cid = (r.get("control_id") or "").strip()
        if not cid:
            continue
        if cid not in controls_by_id:
            problems.append("row %d: control %s is not in the catalogue and was ignored" % (n, cid))
            continue
        if cid not in applicable:
            problems.append("row %d: control %s does not apply to this property and was ignored" % (n, cid))
            continue
        if cid in answers:
            problems.append("row %d: control %s appears twice and the last row was used" % (n, cid))
        raw = (r.get("maturity") or "").strip()
        m = None
        if raw != "":
            try:
                f = float(raw)
                m = int(f) if f == int(f) else None
            except (ValueError, OverflowError):
                m = None
            if m is None or not 0 <= m <= MAX_MATURITY:
                problems.append("row %d: maturity %r for %s is not a whole number from 0 to 4 and was treated as blank"
                                % (n, raw, cid))
                m = None
        evidence = (r.get("evidence_ref") or "").strip()
        if m is not None and m >= 3 and not evidence:
            problems.append("row %d: %s is rated %d but has no evidence reference" % (n, cid, m))
        answers[cid] = {"maturity": m, "evidence_ref": evidence, "comment": (r.get("comment") or "").strip()}
    missing = [c for c in applicable_ids if c not in answers]
    if missing:
        problems.append("%d applicable controls have no row in the questionnaire" % len(missing))
    return answers, problems


def read_assessment(path, controls_by_id, applicable_ids):
    return parse_assessment(read_csv(path), controls_by_id, applicable_ids)
