"""Sensitivity of the rankings to the assumed weights.

Each weight is moved up and down by 20 percent in turn (all other values stay as set). The roadmap is rebuilt and the
ranking of domains by total priority is compared with the base ranking using Spearman rank correlation. Strength
weights change the standard view instead, so their effect is measured on the ranking of frameworks by indicative
coverage. Results are a robustness check on assumed values, not a measure of accuracy.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import domain_sort_key, mean, spearman  # noqa: E402
from roadmap import build_roadmap, domain_priority  # noqa: E402
from score import standard_view  # noqa: E402

FACTORS = (0.8, 1.2)


def scale_setting(cfg, family, key, factor):
    """Copy of the settings with one weight multiplied by factor."""
    c = copy.deepcopy(cfg)
    c[family][key] = c[family][key] * factor
    return c


def _vector(by_key, keys):
    return [by_key.get(k, 0.0) for k in keys]


def roadmap_sensitivity(control_rows, controls_by_id, caps, cfg, top_n=10):
    base_items = build_roadmap(control_rows, controls_by_id, caps, cfg)
    base_dom = domain_priority(base_items)
    domains = sorted(base_dom, key=domain_sort_key)
    base_vec = _vector(base_dom, domains)
    base_top = [i["control_id"] for i in base_items[:top_n]]
    rows = []
    for family in ("level_weights", "tier_weights", "effort_weights"):
        for key in cfg[family]:
            for f in FACTORS:
                c2 = scale_setting(cfg, family, key, f)
                items = build_roadmap(control_rows, controls_by_id, caps, c2)
                rho = spearman(base_vec, _vector(domain_priority(items), domains)) if len(domains) > 1 else None
                top = [i["control_id"] for i in items[:top_n]]
                rows.append({"setting": family, "key": str(key), "factor": f,
                             "domain_rho": round(rho, 3) if rho is not None else None,
                             "top_overlap": len(set(base_top) & set(top)), "top_n": len(base_top)})
    return rows


def framework_sensitivity(control_rows, crosswalk, cfg, universe=None):
    base = standard_view(control_rows, crosswalk, cfg, universe)["frameworks"]
    names = [f["framework"] for f in base]
    key = "indicative_pct_universe" if all(f["indicative_pct_universe"] is not None
                                           for f in base if f["universe_known"]) else "indicative_pct_reached"
    def vec(frs):
        return [(f.get(key) if f.get(key) is not None else f["indicative_pct_reached"] or 0.0) for f in frs]
    base_vec = vec(base)
    rows = []
    for s in cfg["strength_weights"]:
        for f in FACTORS:
            c2 = scale_setting(cfg, "strength_weights", s, f)
            frs = standard_view(control_rows, crosswalk, c2, universe)["frameworks"]
            rho = spearman(base_vec, vec(frs)) if len(names) > 1 else None
            rows.append({"setting": "strength_weights", "key": s, "factor": f,
                         "framework_rho": round(rho, 3) if rho is not None else None})
    return rows


def summarise(rows, field):
    vals = [r[field] for r in rows if r.get(field) is not None]
    if not vals:
        return {"cases": len(rows), "rho_min": None, "rho_mean": None, "rho_max": None}
    return {"cases": len(rows), "rho_min": round(min(vals), 3), "rho_mean": round(mean(vals), 3),
            "rho_max": round(max(vals), 3)}
