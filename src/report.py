"""Write every output file for one run: CSV tables, gap_report.md, results.json and dashboard.html.

    applicability.csv  control_scores.csv  domain_scores.csv  standard_view.csv  jurisdiction_readiness.csv
    gap_report.md  roadmap.csv  iso_only_comparison.csv  results.json  dashboard.html
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from applicability import APPLICABILITY_FIELDS  # noqa: E402
from common import write_csv, write_json, write_text  # noqa: E402
from dashboard import render_dashboard  # noqa: E402
from gap import ISO_ONLY_FIELDS  # noqa: E402
from render_standard import join_and  # noqa: E402
from roadmap import ROADMAP_FIELDS  # noqa: E402
from score import (CONTROL_SCORE_FIELDS, DOMAIN_FIELDS, JURISDICTION_FIELDS, STANDARD_FIELDS)  # noqa: E402

OUTPUT_FILES = ["applicability.csv", "control_scores.csv", "domain_scores.csv", "standard_view.csv",
                "jurisdiction_readiness.csv", "gap_report.md", "roadmap.csv", "iso_only_comparison.csv",
                "results.json", "dashboard.html"]


def input_banner(res):
    inp = res["input"]
    if inp["status"] == "simulated":
        return "The answers in this run are simulated (%s). They show how the toolkit behaves and are not a finding about the property." % (inp["tag"] or "tagged")
    return "The answers in this run are self assessed (%s)." % (inp["status"])


def gap_report_md(res):
    p, ov, g = res["property"], res["overall"], res["gap"]
    L = []
    a = L.append
    a("# Gap report: %s" % p["label"])
    a("")
    a("Toolkit: HISS-Assess. Author: %s." % res["author"])
    a("")
    a("Profile %s, operating model %s, active triggers: %s." % (p["profile"], p["operating_model"],
                                                               join_and(p["triggers"]) or "none"))
    a("")
    a(input_banner(res))
    a("")
    a(res["assumptions"]["note"])
    a("")
    a("## Summary")
    a("")
    a("- Applicable controls: %d of %d in the catalogue." % (res["applicability"]["applicable"], res["applicability"]["total"]))
    a("- Answered: %d. Mean effective maturity %.2f of 4 (%.1f percent)." % (ov["answered"], ov["mean_maturity"], ov["maturity_pct"]))
    a("- Met (maturity %d or above): %d controls (%.1f percent). Unmet: %d." % (
        res["assumptions"]["met_threshold"], ov["met"], ov["met_pct"], g["unmet_total"]))
    if res.get("hissrat"):
        h = res["hissrat"]
        a("- HISS-RAT scan caps lowered the maturity of %d controls (capped by scan). %d controls carry a cap that did not bind. "
          "In scope: %d systems and %d findings." % (
              h["controls_capped"], h["controls_with_cap"] - h["controls_capped"], h["in_scope_systems"], h["in_scope_findings"]))
    a("")
    a("| Domain | Name | Mean maturity percent | Met | Unmet |")
    a("|---|---|---|---|---|")
    for d in res["domains"]:
        a("| %s | %s | %s | %d | %d |" % (d["domain"], d["domain_name"], d["maturity_pct"], d["met"], d["unmet"]))
    a("")
    a("## Unmet controls by domain")
    a("")
    if not g["by_domain"]:
        a("Every applicable control is met.")
        a("")
    for d in g["by_domain"]:
        a("### %s %s" % (d["domain"], d["domain_name"]))
        a("")
        for c in d["controls"]:
            extra = ""
            if c["answered"] != "yes":
                extra += " Not answered."
            if c["cap_reason"]:
                extra += " Capped by: %s." % c["cap_reason"]
            a("- %s %s (%s). Maturity %s.%s" % (c["control_id"], c["title"], c["level"], c["maturity"], extra))
        a("")
    a("## Unmet by standard")
    a("")
    a("Source backed figures use direct (D) rows with verified targets only. Indicative figures use every scored row. "
      "A clause is unmet when no applicable control mapped to it is met.")
    a("")
    a("| Framework | Clauses | Reached | Unreached | Met (indicative) | Met (source backed) | Source backed percent | Indicative percent |")
    a("|---|---|---|---|---|---|---|---|")
    for f in res["standard"]["frameworks"]:
        a("| %s | %s | %d | %d | %d | %d | %s | %s |" % (
            f["name"], f["clauses_total"], f["clauses_reached_applicable"], f["clauses_unreached"],
            f["clauses_met_indicative"], f["clauses_met_source_backed"],
            _fmt(f["source_backed_pct_universe"] if f["universe_known"] else f["source_backed_pct_reached"]),
            _fmt(f["indicative_pct_universe"] if f["universe_known"] else f["indicative_pct_reached"])))
    a("")
    a("Percentages count clauses that no HISS control reaches as zero where the clause list is known. Otherwise they cover reached clauses only.")
    a("")
    for fw, d in sorted(g["by_standard"].items()):
        name = next((f["name"] for f in res["standard"]["frameworks"] if f["framework"] == fw), fw)
        if d["unmet_clauses"]:
            a("Unmet clauses, %s: %s." % (name, limited((c["target_id"] for c in d["unmet_clauses"]), 40)))
            a("")
        if d["unreached"]:
            a("Clauses no HISS control reaches, %s (%d): %s." % (name, len(d["unreached"]),
                                                                  limited((c["target_id"] for c in d["unreached"]), 60)))
            a("")
    if res["standard"]["unknown_targets"]:
        a("Crosswalk targets outside the clause list are scored in standard_view.csv but are not part of the framework percentages: %s." % limited(
            ("%s %s" % (u["framework"], u["target"]) for u in res["standard"]["unknown_targets"]), 30))
        a("")
    a("## Unmet by jurisdiction")
    a("")
    a("Only VERIFIED obligations are scored. SECONDARY obligations are tracked and are not scored.")
    a("")
    a("| Jurisdiction | Basis | Obligations scored | Ready | Partial | Not ready | Tracking | Readiness percent |")
    a("|---|---|---|---|---|---|---|---|")
    for s in res["jurisdictions"]["summary"] + [res["jurisdictions"]["overall"]]:
        a("| %s | %s | %s | %s | %s | %s | %s | %s |" % (s["jurisdiction"], s["basis"], s["obligations_scored"], s["ready_n"],
                                                       s["partial_n"], s["not_ready_n"], s["tracking_n"], _fmt(s["readiness_pct"])))
    a("")
    if g["by_jurisdiction"]:
        a("| Obligation | Jurisdiction | Provision | State | Readiness percent | Unmet controls |")
        a("|---|---|---|---|---|---|")
        for o in g["by_jurisdiction"]:
            a("| %s | %s | %s | %s | %s | %s |" % (o["obligation_id"], o["jurisdiction"], o["provision"].replace("|", "/"), o["state"],
                                                   _fmt(o["readiness_pct"]), o["unmet_controls"]))
        a("")
    trk = [r for r in res["jurisdictions"]["rows"] if r["row_type"] == "tracking"]
    if trk:
        a("Tracking only (SECONDARY, not scored): %s." % join_and("%s %s" % (r["obligation_id"], r["provision"]) for r in trk))
        a("")
    a("## ISO only comparison")
    a("")
    s = g["iso_only"]["summary"]
    a("Each hotel requirement is classed under ISO/IEC 27001 Annex A alone and under HISS (assumption A37). "
      "Under ISO alone: %d specific, %d generic, %d absent. Under HISS: %d specific, %d generic, %d absent. "
      "Requirements counted: %d." % (s["iso_only"]["specific"], s["iso_only"]["generic"], s["iso_only"]["absent"],
                                     s["hiss"]["specific"], s["hiss"]["generic"], s["hiss"]["absent"], s["requirements"]))
    a("")
    if s["manual_file_present"]:
        m = s["iso_only_manual"]
        a("Hand classification (inputs/iso_only_manual.csv): %d specific, %d generic, %d absent, %d not classified. "
          "The automatic rule is circular because the ISO rows were written to cover the requirements, so the hand "
          "classification is the sensitivity check." % (m["specific"], m["generic"], m["absent"], m["unclassified"]))
    else:
        a("No hand classification file was found. The automatic rule is circular because the ISO rows were written to cover "
          "the requirements, so supply inputs/iso_only_manual.csv (req_id, class, reason) as a sensitivity check.")
    a("")
    a("Of %d unmet controls, %d have no direct or partial ISO27001 row, so an ISO only review would not point to them." % (
        s["unmet_controls"], s["unmet_controls_invisible_to_iso_only"]))
    a("")
    if g["iso_only"]["invisible_to_iso"]:
        for c in g["iso_only"]["invisible_to_iso"]:
            a("- %s %s. Maturity %s. ISO27001 rows: %s." % (c["control_id"], c["title"], c["maturity"], c["iso_rows"]))
        a("")
    a("## Roadmap waves")
    a("")
    a("| Wave | Items | Baseline | Enhanced |")
    a("|---|---|---|---|")
    for w in res["roadmap"]["waves"]:
        a("| %s | %d | %d | %d |" % (w["label"], w["items"], w["baseline"], w["enhanced"]))
    a("")
    a("Priority = level weight x tier weight x maturity gap / effort weight. See roadmap.csv for every item.")
    a("")
    ws = res["roadmap"]["wave_sensitivity"]
    a("Wave cut offs are %s for wave 1 and %s for wave 2 (assumed). Moving both by 20 percent changes the wave of %d items "
      "(table below and results.json). Items per wave: %s." % (
          ws["cutoffs"]["wave1"], ws["cutoffs"]["wave2"], len(ws["rows"]),
          "; ".join("%s %d, %d, %d" % (x["scenario"], x["wave1"], x["wave2"], x["wave3"]) for x in ws["summary"])))
    a("")
    if ws["rows"]:
        a("| Control | Title | Level | Priority | Base wave | Cut offs x0.8 | Cut offs x1.2 |")
        a("|---|---|---|---|---|---|---|")
        for r in ws["rows"]:
            a("| %s | %s | %s | %s | %d | %d | %d |" % (r["control_id"], r["title"].replace("|", "/"), r["level"], r["priority"],
                                                       r["wave_base"], r["wave_cutoffs_minus20"], r["wave_cutoffs_plus20"]))
        a("")
    if res["input"]["problems"]:
        a("## Input notes")
        a("")
        for pr in res["input"]["problems"]:
            a("- %s" % pr)
        a("")
    return "\n".join(L)


def limited(items, limit):
    """A, B and C, with a final item such as '12 more' when the list is longer than limit."""
    items = list(items)
    if len(items) <= limit:
        return join_and(items)
    return join_and(items[:limit] + ["%d more" % (len(items) - limit)])


def _fmt(v):
    return "n/a" if v in (None, "") else str(v)


def juris_csv_rows(res):
    j = res["jurisdictions"]
    return j["rows"] + j["summary"] + [j["overall"]]


def write_outputs(res, out_dir):
    """Write all ten output files into out_dir and return their names."""
    write_csv(os.path.join(out_dir, "applicability.csv"), res["applicability"]["rows"], APPLICABILITY_FIELDS)
    write_csv(os.path.join(out_dir, "control_scores.csv"), res["controls"], CONTROL_SCORE_FIELDS)
    write_csv(os.path.join(out_dir, "domain_scores.csv"), res["domains"], DOMAIN_FIELDS)
    write_csv(os.path.join(out_dir, "standard_view.csv"), res["standard"]["rows"], STANDARD_FIELDS)
    write_csv(os.path.join(out_dir, "jurisdiction_readiness.csv"), juris_csv_rows(res), JURISDICTION_FIELDS)
    write_text(os.path.join(out_dir, "gap_report.md"), gap_report_md(res))
    write_csv(os.path.join(out_dir, "roadmap.csv"), res["roadmap"]["items"], ROADMAP_FIELDS)
    write_csv(os.path.join(out_dir, "iso_only_comparison.csv"), res["gap"]["iso_only"]["rows"], ISO_ONLY_FIELDS)
    write_json(os.path.join(out_dir, "results.json"), res)
    write_text(os.path.join(out_dir, "dashboard.html"), render_dashboard(res))
    return list(OUTPUT_FILES)
