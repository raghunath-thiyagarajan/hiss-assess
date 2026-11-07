"""Gap analysis: unmet controls by domain, by standard and by jurisdiction plus the ISO only comparison.

ISO only comparison (assumption A37). For every hotel requirement the toolkit gives two classes.
  HISS class: specific when at least one catalogue control is linked to the requirement, otherwise absent.
  ISO class:  generic when a linked control has an ISO27001 crosswalk row of strength D or P (the Annex A clause
              covers the theme in general terms), absent when the only ISO27001 rows are J or there are none.
              A requirement counts as specific under ISO only when its id is listed in the setting
              iso_only_specific_req_ids, which records a manual judgement.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import domain_sort_key  # noqa: E402

ISO_ONLY_FIELDS = ["req_id", "text", "c1_ref", "hiss_controls", "hiss_class", "iso_targets", "iso_best_strength",
                   "iso_class", "applicable_controls", "unmet_controls", "iso_class_manual", "manual_reason"]
CLASSES = ("specific", "generic", "absent")


def parse_iso_manual(rows, known_req_ids):
    """Read the hand classification rows (req_id, class, reason). Returns (manual, problems)."""
    manual, problems = {}, []
    for n, r in enumerate(rows, 2):
        rid = (r.get("req_id") or "").strip()
        cls = (r.get("class") or "").strip().lower()
        if not rid:
            continue
        if rid not in known_req_ids:
            problems.append("iso_only_manual.csv row %d: requirement %s is not in requirements.csv and was ignored" % (n, rid))
        elif cls not in CLASSES:
            problems.append("iso_only_manual.csv row %d: class %r for %s is not specific, generic or absent and was ignored" % (n, cls, rid))
        else:
            manual[rid] = {"class": cls, "reason": (r.get("reason") or "").strip()}
    return manual, problems


def unmet_by_domain(control_rows, domain_names=None):
    """Unmet controls grouped by domain, worst first inside each domain."""
    domain_names = domain_names or {}
    groups = defaultdict(list)
    for r in control_rows:
        if r["met"] != "yes":
            groups[r["domain"]].append(r)
    out = []
    for d in sorted(groups, key=domain_sort_key):
        items = sorted(groups[d], key=lambda r: (r["maturity"], r["control_id"]))
        out.append({"domain": d, "domain_name": domain_names.get(d, d), "unmet": len(items),
                    "controls": [{"control_id": r["control_id"], "title": r["title"], "level": r["level"],
                                  "maturity": r["maturity"], "answered": r["answered"], "cap_reason": r["cap_reason"]}
                                 for r in items]})
    return out


def unmet_by_standard(standard_rows):
    """Per framework: clauses reached by applicable controls where no mapped control is met plus unreached clauses."""
    out = defaultdict(lambda: {"unmet_clauses": [], "unreached": []})
    for r in standard_rows:
        if r["state"] == "scored" and r["met"] == "no":
            out[r["framework"]]["unmet_clauses"].append({"target_id": r["target_id"], "target_title": r["target_title"],
                                                         "controls": r["controls"],
                                                         "indicative_pct": r["indicative_pct"]})
        elif r["state"] == "not reached by any HISS control":
            out[r["framework"]]["unreached"].append({"target_id": r["target_id"], "target_title": r["target_title"]})
    return dict(out)


def unmet_by_jurisdiction(readiness_rows):
    """Scored obligations that are not ready, with the unmet controls behind them."""
    out = []
    for r in readiness_rows:
        if r["row_type"] == "obligation" and r["state"] in ("not ready", "partial", "no applicable control"):
            out.append({"jurisdiction": r["jurisdiction"], "basis": r["basis"], "obligation_id": r["obligation_id"],
                        "instrument": r["instrument"], "provision": r["provision"], "state": r["state"],
                        "readiness_pct": r["readiness_pct"], "unmet_controls": r["unmet_controls"]})
    return out


def iso_only_comparison(catalogue, control_rows, cfg, manual=None):
    """Requirement level classes under ISO only and under HISS, plus unmet controls an ISO only review would miss.

    The automatic ISO class is circular: the catalogue author wrote the ISO rows to cover the requirements, so a
    requirement almost always comes out generic. The optional manual classification (inputs/iso_only_manual.csv,
    passed in as manual) is a hand judgement and is reported next to it as the sensitivity.
    """
    manual = manual or {}
    by_id = catalogue["control_by_id"]
    iso_rows = defaultdict(list)
    for x in catalogue["crosswalk"]:
        if x["framework"] == "ISO27001" and x["target_status"] != "NOT VERIFIED":
            iso_rows[x["control_id"]].append(x)
    met = {r["control_id"]: r["met"] for r in control_rows}
    forced_specific = set(cfg.get("iso_only_specific_req_ids") or [])
    rows = []
    for req in catalogue["requirements"]:
        linked = [c for c in (req.get("control_list") or []) if c in by_id]
        targets = {}
        for cid in linked:
            for x in iso_rows.get(cid, []):
                old = targets.get(x["target_id"])
                if old is None or "DPJ".index(x["strength"]) < "DPJ".index(old):
                    targets[x["target_id"]] = x["strength"]
        strengths = set(targets.values())
        best = "D" if "D" in strengths else "P" if "P" in strengths else "J" if "J" in strengths else ""
        if req["req_id"] in forced_specific:
            iso_class = "specific"
        elif best in ("D", "P"):
            iso_class = "generic"
        else:
            iso_class = "absent"
        hiss_class = "specific" if linked else "absent"
        applic = [c for c in linked if c in met]
        rows.append({
            "req_id": req["req_id"], "text": req["text"], "c1_ref": req.get("c1_ref", ""),
            "hiss_controls": "; ".join(linked), "hiss_class": hiss_class,
            "iso_targets": "; ".join("%s (%s)" % (t, s) for t, s in sorted(targets.items())),
            "iso_best_strength": best, "iso_class": iso_class,
            "applicable_controls": len(applic), "unmet_controls": sum(1 for c in applic if met[c] != "yes"),
            "iso_class_manual": manual.get(req["req_id"], {}).get("class", ""),
            "manual_reason": manual.get(req["req_id"], {}).get("reason", ""),
        })
    matrix = {i: {h: sum(1 for r in rows if r["iso_class"] == i and r["hiss_class"] == h) for h in CLASSES} for i in CLASSES}
    invisible = []
    for r in control_rows:
        if r["met"] == "yes":
            continue
        s = {x["strength"] for x in iso_rows.get(r["control_id"], [])}
        if not (s & {"D", "P"}):
            invisible.append({"control_id": r["control_id"], "title": r["title"], "maturity": r["maturity"],
                              "iso_rows": "none" if not s else "J only"})
    summary = {
        "requirements": len(rows),
        "iso_only": {c: sum(1 for r in rows if r["iso_class"] == c) for c in CLASSES},
        "hiss": {c: sum(1 for r in rows if r["hiss_class"] == c) for c in CLASSES},
        "matrix_iso_by_hiss": matrix,
        "manual_file_present": bool(manual),
        "iso_only_manual": {**{c: sum(1 for r in rows if r["iso_class_manual"] == c) for c in CLASSES},
                            "unclassified": sum(1 for r in rows if not r["iso_class_manual"])},
        "matrix_manual_by_hiss": {i: {h: sum(1 for r in rows if r["iso_class_manual"] == i and r["hiss_class"] == h)
                                      for h in CLASSES} for i in CLASSES},
        "unmet_controls": sum(1 for r in control_rows if r["met"] != "yes"),
        "unmet_controls_invisible_to_iso_only": len(invisible),
    }
    return {"rows": rows, "summary": summary, "invisible_to_iso": invisible}


def build_gap(control_rows, standard, readiness, catalogue, cfg, domain_names=None, iso_manual=None):
    return {
        "by_domain": unmet_by_domain(control_rows, domain_names),
        "by_standard": unmet_by_standard(standard["rows"]),
        "by_jurisdiction": unmet_by_jurisdiction(readiness["rows"]),
        "iso_only": iso_only_comparison(catalogue, control_rows, cfg, iso_manual),
        "unmet_total": sum(1 for r in control_rows if r["met"] != "yes"),
        "controls_total": len(control_rows),
    }
