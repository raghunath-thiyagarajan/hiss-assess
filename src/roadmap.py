"""Remediation roadmap from the unmet controls.

    priority = level weight x tier weight of the affected systems x maturity gap / effort weight

  level weight   Baseline or Enhanced, from the settings (assumed, A30)
  tier weight    Capstone 1 tier weight of the most critical affected system. Affected systems come from the HISS-RAT
                 caps. A control with no HISS-RAT evidence uses the default tier of its domain (assumed, A29)
  maturity gap   target maturity minus current effective maturity, never below zero
  effort weight  S, M or L from the settings (assumed, A29)

Waves are set by priority cut offs in the settings: wave 1 is 0 to 90 days, wave 2 is 3 to 6 months and
wave 3 is 6 to 12 months. A control id listed in wave_overrides takes the wave given there.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import domain_sort_key  # noqa: E402

ROADMAP_FIELDS = ["rank", "control_id", "domain", "title", "level", "maturity", "target", "gap", "level_weight", "tier",
                  "tier_weight", "tier_source", "effort", "effort_weight", "priority", "wave", "wave_label",
                  "accountable", "drivers", "systems"]


def effort_of(control_id, domain, cfg):
    """Effort size S, M or L: per control setting, then per domain setting, then the default."""
    for table, key in ((cfg["effort_by_control"], control_id), (cfg["effort_by_domain"], domain)):
        v = table.get(key)
        if v in cfg["effort_weights"]:
            return v
    return cfg["default_effort"] if cfg["default_effort"] in cfg["effort_weights"] else "M"


def tier_of(domain, cap_info, cfg):
    """Return (tier number, tier weight, source text)."""
    tiers = cap_info.get("tiers") if cap_info else None
    if tiers:
        t = min(tiers)
        if t in cfg["tier_weights"]:
            return t, cfg["tier_weights"][t], "HISS-RAT affected systems"
    t = cfg["domain_default_tier"].get(domain, cfg["default_tier"])
    return t, cfg["tier_weights"].get(t, min(cfg["tier_weights"].values())), "domain default (assumed)"


def priority_of(level_weight, tier_weight, gap, effort_weight):
    return level_weight * tier_weight * gap / effort_weight


def wave_of(control_id, priority, cfg):
    over = cfg["wave_overrides"].get(control_id)
    if over in (1, 2, 3):
        return over
    w = cfg["waves"]
    if priority >= w["wave1_min_priority"]:
        return 1
    if priority >= w["wave2_min_priority"]:
        return 2
    return 3


def build_roadmap(control_rows, controls_by_id, caps, cfg):
    """Roadmap items for every control below the target maturity, highest priority first."""
    items = []
    target = cfg["target_maturity"]
    labels = cfg["waves"]["labels"]
    for r in control_rows:
        gap = max(0, target - r["maturity"])
        if gap == 0:
            continue
        cid, dom = r["control_id"], r["domain"]
        cap = caps.get(cid)
        tier, tw, tsrc = tier_of(dom, cap, cfg)
        lw = cfg["level_weights"][r["level"]]
        eff = effort_of(cid, dom, cfg)
        ew = cfg["effort_weights"][eff]
        pr = priority_of(lw, tw, gap, ew)
        wave = wave_of(cid, pr, cfg)
        drivers = "; ".join(cap["reasons"][:2]) if cap else ""
        if r["answered"] != "yes":
            drivers = (drivers + "; " if drivers else "") + "not assessed"
        items.append({
            "control_id": cid, "domain": dom, "title": r["title"], "level": r["level"], "maturity": r["maturity"],
            "target": target, "gap": gap, "level_weight": lw, "tier": tier, "tier_weight": tw, "tier_source": tsrc,
            "effort": eff, "effort_weight": ew, "priority": round(pr, 2), "wave": wave,
            "wave_label": labels.get(str(wave), "Wave %d" % wave), "accountable": r["accountable"],
            "drivers": drivers, "systems": "; ".join(cap["systems"][:5]) if cap else "",
            "_priority_exact": pr,
        })
    items.sort(key=lambda i: (-i["_priority_exact"], domain_sort_key(i["domain"]), i["control_id"]))
    for n, i in enumerate(items, 1):
        i["rank"] = n
    return items


def public_items(items):
    """Items without the internal exact priority, ready to write."""
    return [{k: v for k, v in i.items() if not k.startswith("_")} for i in items]


def wave_summary(items, cfg):
    out = []
    for w in (1, 2, 3):
        mine = [i for i in items if i["wave"] == w]
        out.append({"wave": w, "label": cfg["waves"]["labels"].get(str(w), "Wave %d" % w), "items": len(mine),
                    "baseline": sum(1 for i in mine if i["level"] == "Baseline"),
                    "enhanced": sum(1 for i in mine if i["level"] == "Enhanced"),
                    "priority_sum": round(sum(i["_priority_exact"] for i in mine), 2)})
    return out


WAVE_SENSITIVITY_FIELDS = ["control_id", "domain", "title", "level", "priority", "wave_base", "wave_cutoffs_minus20",
                           "wave_cutoffs_plus20", "changes"]


def wave_cutoff_sensitivity(items, cfg, factors=(0.8, 1.2)):
    """Which items change wave when both priority cut offs move by 20 percent down and up.

    items are the internal roadmap items (with the exact priority). Manual wave overrides stay in force.
    Returns {"rows": [...], "summary": [...], "cutoffs": {...}}. Rows list only items whose wave changes.
    """
    w = cfg["waves"]
    base = (w["wave1_min_priority"], w["wave2_min_priority"])
    scen = {}
    for f in factors:
        c2 = dict(cfg)
        c2["waves"] = dict(w, wave1_min_priority=base[0] * f, wave2_min_priority=base[1] * f)
        scen[f] = {i["control_id"]: wave_of(i["control_id"], i["_priority_exact"], c2) for i in items}
    rows = []
    for i in items:
        lo, hi = scen[factors[0]][i["control_id"]], scen[factors[1]][i["control_id"]]
        if lo != i["wave"] or hi != i["wave"]:
            rows.append({"control_id": i["control_id"], "domain": i["domain"], "title": i["title"], "level": i["level"],
                         "priority": i["priority"], "wave_base": i["wave"], "wave_cutoffs_minus20": lo,
                         "wave_cutoffs_plus20": hi,
                         "changes": "moves earlier when cut offs fall and later when they rise" if (lo < i["wave"] and hi > i["wave"])
                         else ("moves earlier when cut offs fall" if lo < i["wave"] else "moves later when cut offs rise")})
    summary = []
    for label, waves in (("base", {i["control_id"]: i["wave"] for i in items}),
                         ("cut offs x0.8", scen[factors[0]]), ("cut offs x1.2", scen[factors[1]])):
        summary.append({"scenario": label, **{"wave%d" % k: sum(1 for v in waves.values() if v == k) for k in (1, 2, 3)}})
    return {"rows": rows, "summary": summary,
            "cutoffs": {"wave1": base[0], "wave2": base[1],
                        "minus20": [round(base[0] * factors[0], 2), round(base[1] * factors[0], 2)],
                        "plus20": [round(base[0] * factors[1], 2), round(base[1] * factors[1], 2)]}}


def domain_priority(items):
    """Sum of exact priorities per domain."""
    out = defaultdict(float)
    for i in items:
        out[i["domain"]] += i["_priority_exact"]
    return dict(out)
