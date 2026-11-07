"""Scoring: control, domain, property and group maturity, standard view and jurisdiction readiness.

Every function takes plain lists and dicts and returns plain lists and dicts, so it can be tested without files.

Definitions (all weights and thresholds come from the settings and are assumed values):
  effective maturity  = min(self assessed maturity, finding cap). An unanswered control counts as unanswered_as (default 0).
  capped_by_scan      = yes only when the cap lowered the final maturity (the single meaning of capped everywhere).
                        The column capped repeats the same value for older files.
  met                 = effective maturity at or above met_threshold (default 3).
  domain maturity     = mean effective maturity of the applicable controls in the domain, also shown as a percentage of 4.
  standard coverage   = for each target clause, the maximum over mapped applicable controls of weight(strength) x maturity / 4,
                        with weights D 1.0, P 0.5 and J 0.25. Source backed uses D rows with a VERIFIED target only.
                        Indicative uses every row except NOT VERIFIED targets.
  jurisdiction ready  = for each VERIFIED obligation, mean effective maturity of its applicable linked controls as a
                        percentage of 4. SECONDARY obligations are listed as tracking and never scored.
"""
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from applicability import jurisdiction_matches, obligation_scope  # noqa: E402
from common import MAX_MATURITY, domain_sort_key, mean, pct  # noqa: E402
from ingest_hissrat import apply_cap  # noqa: E402

CONTROL_SCORE_FIELDS = ["control_id", "domain", "title", "level", "accountable", "answered", "self_maturity", "cap",
                        "capped", "capped_by_scan", "cap_reason", "maturity", "met", "evidence_ref", "comment"]
DOMAIN_FIELDS = ["domain", "domain_name", "controls", "answered", "mean_maturity", "maturity_pct", "met", "met_pct",
                 "unmet", "capped", "capped_by_scan"]
STANDARD_FIELDS = ["framework", "target_id", "target_title", "target_status", "controls", "mapped_controls",
                   "direct_rows", "source_backed_pct", "indicative_pct", "best_control", "met", "state"]
JURISDICTION_FIELDS = ["row_type", "jurisdiction", "basis", "obligation_id", "tag", "instrument", "provision", "status",
                       "linked_controls", "applicable_controls", "met_controls", "unmet_controls", "mean_maturity",
                       "readiness_pct", "state", "obligations_scored", "ready_n", "partial_n", "not_ready_n",
                       "no_control_n", "tracking_n"]

STATUS_ORDER = {"VERIFIED": 0, "SECONDARY": 1, "NOT VERIFIED": 2}


# ---------------------------------------------------------------- controls

def score_controls(app_rows, controls_by_id, answers, caps, cfg):
    """One row per applicable control with self assessed, cap and effective maturity."""
    threshold = cfg["met_threshold"]
    unanswered = cfg["unanswered_as"]
    rows = []
    for a in app_rows:
        if a["applicable"] != "yes":
            continue
        cid = a["control_id"]
        c = controls_by_id[cid]
        ans = answers.get(cid) or {}
        selfm = ans.get("maturity")
        answered = selfm is not None
        base = selfm if answered else unanswered
        cap_info = caps.get(cid)
        cap = cap_info["cap"] if cap_info else None
        eff = apply_cap(base, cap)
        lowered = "yes" if eff < base else "no"
        rows.append({
            "control_id": cid, "domain": c["domain"], "title": c["title"], "level": c["level"],
            "accountable": a["accountable"], "answered": "yes" if answered else "no",
            "self_maturity": selfm if answered else "",
            "cap": cap if cap is not None else "",
            "capped": lowered, "capped_by_scan": lowered,
            "cap_reason": "; ".join(cap_info["reasons"]) if cap_info else "",
            "maturity": eff, "met": "yes" if eff >= threshold else "no",
            "evidence_ref": ans.get("evidence_ref", ""), "comment": ans.get("comment", ""),
        })
    return rows


def domain_scores(control_rows, domain_names=None):
    """Mean effective maturity per domain, in domain order."""
    domain_names = domain_names or {}
    groups = defaultdict(list)
    for r in control_rows:
        groups[r["domain"]].append(r)
    out = []
    for d in sorted(groups, key=domain_sort_key):
        rows = groups[d]
        m = mean(r["maturity"] for r in rows)
        met = sum(1 for r in rows if r["met"] == "yes")
        out.append({
            "domain": d, "domain_name": domain_names.get(d, d), "controls": len(rows),
            "answered": sum(1 for r in rows if r["answered"] == "yes"),
            "mean_maturity": round(m, 2), "maturity_pct": round(100.0 * m / MAX_MATURITY, 1),
            "met": met, "met_pct": round(100.0 * met / len(rows), 1), "unmet": len(rows) - met,
            "capped": sum(1 for r in rows if r["capped_by_scan"] == "yes"),
            "capped_by_scan": sum(1 for r in rows if r["capped_by_scan"] == "yes"),
        })
    return out


def property_score(control_rows, domain_rows):
    """Property level maturity: control weighted mean and mean of domain percentages."""
    n = len(control_rows)
    if n == 0:
        return {"controls": 0, "answered": 0, "completeness_pct": 0.0, "mean_maturity": 0.0, "maturity_pct": 0.0,
                "met": 0, "met_pct": 0.0, "domain_mean_pct": 0.0, "capped_by_scan": 0}
    m = mean(r["maturity"] for r in control_rows)
    met = sum(1 for r in control_rows if r["met"] == "yes")
    ans = sum(1 for r in control_rows if r["answered"] == "yes")
    return {"controls": n, "answered": ans, "completeness_pct": round(100.0 * ans / n, 1),
            "mean_maturity": round(m, 2), "maturity_pct": round(100.0 * m / MAX_MATURITY, 1),
            "met": met, "met_pct": round(100.0 * met / n, 1),
            "capped_by_scan": sum(1 for r in control_rows if r["capped_by_scan"] == "yes"),
            "domain_mean_pct": round(mean(d["maturity_pct"] for d in domain_rows), 1) if domain_rows else 0.0}


def group_maturity(property_results):
    """Roll several property results up to a group view.

    property_results is a list of dicts with keys property, overall (from property_score) and domains (from domain_scores).
    Group maturity is the plain mean of the property percentages, so a large property does not outweigh a small one.
    """
    props = [p["property"] for p in property_results]
    matrix = defaultdict(dict)
    for p in property_results:
        for d in p["domains"]:
            matrix[d["domain"]][p["property"]] = d["maturity_pct"]
    return {
        "properties": props,
        "group_maturity_pct": round(mean(p["overall"]["maturity_pct"] for p in property_results), 1) if property_results else 0.0,
        "group_met_pct": round(mean(p["overall"]["met_pct"] for p in property_results), 1) if property_results else 0.0,
        "domain_matrix": {d: dict(matrix[d]) for d in sorted(matrix, key=domain_sort_key)},
        "domain_mean_pct": {d: round(mean(matrix[d].values()), 1) for d in sorted(matrix, key=domain_sort_key)},
    }


# ---------------------------------------------------------------- standard view

def clause_key(framework, target_id):
    """Roll a target id up to the clause granularity used for the clause lists.

    ISO controls stay as A.<theme>.<n>; PCI DSS becomes the principal requirement; CSF becomes the category;
    CIS becomes the control number; CCM becomes the domain code.
    """
    t = (target_id or "").strip().upper()
    if framework == "ISO27001":
        t = re.sub(r"^(ISO\s*)?(27001\s*)?", "", t).strip()
        return "A." + t if re.match(r"^\d+\.\d+$", t) else t
    if framework == "PCIDSS":
        m = re.search(r"\d+", t)
        return m.group(0) if m else t
    if framework == "CSF":
        return re.split(r"[-\s]", t)[0]
    if framework == "CIS":
        m = re.search(r"\d+", t)
        return m.group(0) if m else t
    if framework == "CCM":
        return re.split(r"[-\s]", t)[0]
    return t


def standard_view(control_rows, crosswalk, cfg, universe=None):
    """Clause level coverage for every framework.

    universe is {framework: [{"id", "title"}]} or None. Returns {"rows", "frameworks", "unknown_targets"}.
    """
    weights = cfg["strength_weights"]
    threshold = cfg["met_threshold"]
    mat = {r["control_id"]: r["maturity"] for r in control_rows}
    universe = universe or {}
    uni_ids = {fw: {clause_key(fw, u["id"]) for u in lst} for fw, lst in universe.items()}
    uni_titles = {fw: {u["title"].strip().lower(): clause_key(fw, u["id"]) for u in lst if u.get("title")}
                  for fw, lst in universe.items()}

    def resolve(fw, tid):
        """Clause key for a target. A target given as a full title is matched to its clause code when the list has it."""
        key = clause_key(fw, tid)
        known = uni_ids.get(fw)
        if known is None or key in known:
            return key
        return uni_titles.get(fw, {}).get((tid or "").strip().lower(), key)

    groups = {}
    for x in crosswalk:
        g = groups.setdefault((x["framework"], x["target_id"]), {"title": x.get("target_title", ""), "rows": []})
        g["rows"].append(x)

    rows, clause_best, detail = [], {}, defaultdict(dict)
    for (fw, tid), g in groups.items():
        statuses = {x["target_status"] for x in g["rows"]}
        status = max(statuses, key=lambda s: STATUS_ORDER.get(s, 3))
        scorable = [x for x in g["rows"] if x["target_status"] != "NOT VERIFIED"]
        mapped = [x for x in scorable if x["control_id"] in mat]
        key = resolve(fw, tid)
        entry = clause_best.setdefault((fw, key), {"reached": False, "applicable": False, "backed": 0.0, "indicative": 0.0,
                                                   "met": False, "met_backed": False})
        if scorable:
            entry["reached"] = True
        if not scorable:
            state = "excluded (NOT VERIFIED target)"
        elif not mapped:
            state = "no applicable control"
        else:
            state = "scored"
        indicative = backed = 0.0
        best = None
        met = False
        direct = 0
        for x in mapped:
            m = mat[x["control_id"]]
            s = x["strength"]
            val = weights[s] * m / MAX_MATURITY
            if val > indicative:
                indicative = val
            if m >= threshold:
                met = True
            if s == "D" and x["target_status"] == "VERIFIED":
                direct += 1
                if val > backed:
                    backed = val
                if m >= threshold:
                    entry["met_backed"] = True
            rank = (val, 1 if s == "D" else 0)
            if best is None or rank > best[0]:
                best = (rank, x["control_id"])
        if mapped and state == "scored" and tid.strip().upper() != key:
            detail[fw][tid] = (backed, indicative)
        if mapped:
            entry["applicable"] = True
            entry["indicative"] = max(entry["indicative"], indicative)
            entry["backed"] = max(entry["backed"], backed)
            entry["met"] = entry["met"] or met
        rows.append({
            "framework": fw, "target_id": tid, "target_title": g["title"], "target_status": status,
            "controls": "; ".join("%s (%s)" % (x["control_id"], x["strength"])
                                  for x in sorted(g["rows"], key=lambda r: r["control_id"])),
            "mapped_controls": len(mapped), "direct_rows": direct,
            "source_backed_pct": pct(backed) if state == "scored" else "",
            "indicative_pct": pct(indicative) if state == "scored" else "",
            "best_control": best[1] if best else "", "met": ("yes" if met else "no") if mapped else "",
            "state": state,
        })

    summaries, unknown = [], []
    fw_order = [f for f in ("ISO27001", "PCIDSS", "CSF", "CIS", "CCM", "SP1800-27", "HTNG")]
    fws = [f for f in fw_order if any(k[0] == f for k in clause_best) or f in universe]
    for fw in fws:
        seen = {k[1]: v for k, v in clause_best.items() if k[0] == fw}
        reached = {k: v for k, v in seen.items() if v["reached"]}
        uni = universe.get(fw)
        ids = [clause_key(fw, u["id"]) for u in uni] if uni else None
        titles = {clause_key(fw, u["id"]): u["title"] for u in uni} if uni else {}
        other = []
        if ids is not None:
            other = [k for k in reached if k not in ids]
            for k in seen:
                if k not in ids:
                    unknown.append({"framework": fw, "target": k})
            unreached = [k for k in ids if k not in reached]
            for k in (u for u in unreached if u not in seen):
                rows.append({"framework": fw, "target_id": k, "target_title": titles.get(k, ""),
                             "target_status": "", "controls": "", "mapped_controls": 0, "direct_rows": 0,
                             "source_backed_pct": "", "indicative_pct": "", "best_control": "", "met": "",
                             "state": "not reached by any HISS control"})
            total = len(ids)
            reached_in_uni = [k for k in ids if k in reached]
        else:
            unreached, total, reached_in_uni = [], len(reached), list(reached)
        app = [reached[k] for k in reached_in_uni if reached[k]["applicable"]]
        s = {
            "framework": fw, "name": None, "universe_known": ids is not None, "clauses_total": total,
            "clauses_reached": len(reached_in_uni), "clauses_reached_applicable": len(app),
            "clauses_unreached": len(unreached), "unreached": unreached,
            "clauses_met_indicative": sum(1 for v in app if v["met"]),
            "clauses_met_source_backed": sum(1 for v in app if v["met_backed"]),
            "source_backed_pct_reached": pct(mean(v["backed"] for v in app)) if app else None,
            "indicative_pct_reached": pct(mean(v["indicative"] for v in app)) if app else None,
        }
        det = list(detail.get(fw, {}).values())
        s["sub_level_clauses"] = len(det)
        s["sub_level_source_backed_pct"] = pct(mean(d[0] for d in det)) if det else None
        s["sub_level_indicative_pct"] = pct(mean(d[1] for d in det)) if det else None
        other_app = [reached[k] for k in other if reached[k]["applicable"]]
        s["other_reached_ids"] = sorted(other)
        s["other_source_backed_pct"] = pct(mean(v["backed"] for v in other_app)) if other_app else None
        s["other_indicative_pct"] = pct(mean(v["indicative"] for v in other_app)) if other_app else None
        if ids is not None and total:
            s["source_backed_pct_universe"] = pct(sum(v["backed"] for v in app) / total)
            s["indicative_pct_universe"] = pct(sum(v["indicative"] for v in app) / total)
        else:
            s["source_backed_pct_universe"] = None
            s["indicative_pct_universe"] = None
        summaries.append(s)
    rows.sort(key=lambda r: (fw_order.index(r["framework"]) if r["framework"] in fw_order else 99,
                             _id_sort(r["target_id"])))
    return {"rows": rows, "frameworks": summaries, "unknown_targets": unknown}


def _id_sort(tid):
    parts = re.split(r"[.\-]", str(tid))
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in parts]


# ---------------------------------------------------------------- jurisdictions

def jurisdiction_readiness(obligations, control_rows, cfg):
    """Readiness per VERIFIED obligation plus roll ups. SECONDARY obligations are listed as tracking only."""
    mat = {r["control_id"]: r["maturity"] for r in control_rows}
    threshold = cfg["met_threshold"]
    rows, out_of_scope = [], []
    groups = defaultdict(list)
    tracking = defaultdict(int)
    for o in obligations:
        ok, basis, reason = obligation_scope(o, cfg)
        if not ok:
            out_of_scope.append({"obligation_id": o["obligation_id"], "jurisdiction": o["jurisdiction"], "reason": reason})
            continue
        conf = next(c for c in cfg["jurisdictions"] if jurisdiction_matches(o["jurisdiction"], c))
        linked = o.get("control_list") or [x.strip() for x in o.get("control_ids", "").split(";") if x.strip()]
        applic = [c for c in linked if c in mat]
        met = [c for c in applic if mat[c] >= threshold]
        unmet = [c for c in applic if mat[c] < threshold]
        mm = mean(mat[c] for c in applic) if applic else None
        row = {"row_type": "obligation", "jurisdiction": conf, "basis": basis, "obligation_id": o["obligation_id"],
               "tag": o["jurisdiction"], "instrument": o["instrument"], "provision": o["provision"], "status": o["status"],
               "linked_controls": len(linked), "applicable_controls": len(applic), "met_controls": len(met),
               "unmet_controls": "; ".join(unmet), "mean_maturity": round(mm, 2) if mm is not None else "",
               "readiness_pct": round(100.0 * mm / MAX_MATURITY, 1) if mm is not None else ""}
        if o["status"] != "VERIFIED":
            row["row_type"] = "tracking"
            row["state"] = "tracking (not scored)"
            row["readiness_pct"] = ""
            tracking[conf] += 1
        elif not applic:
            row["state"] = "no applicable control"
        elif len(met) == len(applic):
            row["state"] = "ready"
        elif not met:
            row["state"] = "not ready"
        else:
            row["state"] = "partial"
        rows.append(row)
        groups[conf].append(row)

    summary = []
    for conf in cfg["jurisdictions"]:
        scored = [r for r in groups.get(conf, []) if r["row_type"] == "obligation"]
        withc = [r for r in scored if r["readiness_pct"] != ""]
        summary.append(_summary_row(conf, cfg["jurisdictions"][conf], scored, withc, tracking.get(conf, 0)))
    all_scored = [r for rs in groups.values() for r in rs if r["row_type"] == "obligation"]
    all_with = [r for r in all_scored if r["readiness_pct"] != ""]
    overall = _summary_row("ALL", "all configured jurisdictions", all_scored, all_with, sum(tracking.values()))
    return {"rows": rows, "summary": summary, "overall": overall, "out_of_scope": out_of_scope}


def _summary_row(conf, basis, scored, withc, tracking):
    r = {"row_type": "summary", "jurisdiction": conf, "basis": basis, "obligations_scored": len(scored),
         "ready_n": sum(1 for x in scored if x["state"] == "ready"),
         "partial_n": sum(1 for x in scored if x["state"] == "partial"),
         "not_ready_n": sum(1 for x in scored if x["state"] == "not ready"),
         "no_control_n": sum(1 for x in scored if x["state"] == "no applicable control"),
         "tracking_n": tracking,
         "readiness_pct": round(mean(x["readiness_pct"] for x in withc), 1) if withc else ""}
    r["state"] = "no scored obligations" if not scored else ""
    return r
