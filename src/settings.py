"""Settings for one assessment run: defaults, the config file and per property overrides.

All weights, caps, effort sizes and cut offs are assumed values (see the README). They live in
config/assessment_config.json and are merged over the defaults below, so a short config file is enough.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import read_json  # noqa: E402

DEFAULTS = {
    "profile": "M",
    "operating_model": "owned",
    "triggers": [],
    "jurisdictions": {},
    "input_status": "self assessed",
    "input_tag": "",
    "met_threshold": 3,
    "target_maturity": 3,
    "unanswered_as": 0,
    "strength_weights": {"D": 1.0, "P": 0.5, "J": 0.25},
    "finding_caps": {"Critical": 1, "High": 1, "Medium": 2},
    "level_weights": {"Baseline": 2.0, "Enhanced": 1.0},
    "tier_weights": {1: 5, 2: 3, 3: 2, 4: 1},
    "default_tier": 2,
    "domain_default_tier": {},
    "effort_weights": {"S": 1, "M": 2, "L": 3},
    "effort_person_days": {"S": "1 to 5", "M": "5 to 20", "L": "20 to 60"},
    "default_effort": "M",
    "effort_by_domain": {},
    "effort_by_control": {},
    "waves": {"wave1_min_priority": 10, "wave2_min_priority": 4,
              "labels": {"1": "Wave 1 (0 to 90 days)", "2": "Wave 2 (3 to 6 months)", "3": "Wave 3 (6 to 12 months)"}},
    "wave_overrides": {},
    "iso_only_specific_req_ids": [],
    "hissrat": {"role_tier": {}, "properties": None},
    "label": "",
}


def _merge(base, over):
    """Merge over into a copy of base. Dict values merge one level deep; everything else is replaced."""
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            merged = dict(out[k])
            for k2, v2 in v.items():
                if isinstance(v2, dict) and isinstance(merged.get(k2), dict):
                    inner = dict(merged[k2])
                    inner.update(v2)
                    merged[k2] = inner
                else:
                    merged[k2] = v2
            out[k] = merged
        else:
            out[k] = copy.deepcopy(v)
    return out


def _normalise(cfg):
    cfg["tier_weights"] = {int(k): float(v) for k, v in cfg["tier_weights"].items()}
    cfg["domain_default_tier"] = {k: int(v) for k, v in cfg["domain_default_tier"].items()}
    cfg["default_tier"] = int(cfg["default_tier"])
    if isinstance(cfg["jurisdictions"], (list, tuple)):
        cfg["jurisdictions"] = {t: "configured" for t in cfg["jurisdictions"]}
    cfg["triggers"] = [str(t).strip().upper() for t in cfg["triggers"]]
    cfg["profile"] = str(cfg["profile"]).strip().upper()
    cfg["operating_model"] = str(cfg["operating_model"]).strip().lower()
    return cfg


def load_config(path=None):
    """Read a config file (or use the defaults when path is None) and return the full settings dict."""
    raw = read_json(path) if path else {}
    return raw


def property_settings(raw, name):
    """Settings for one property: defaults, then the top level of the config file, then properties[NAME]."""
    raw = raw or {}
    top = {k: v for k, v in raw.items() if k != "properties" and not k.startswith("_")}
    cfg = _merge(DEFAULTS, top)
    over = {}
    for key, val in (raw.get("properties") or {}).items():
        if key.upper() == str(name).upper():
            over = val
            break
    cfg = _merge(cfg, over)
    cfg["property"] = str(name)
    if not cfg.get("label"):
        cfg["label"] = str(name)
    return _normalise(cfg)


def check_settings(cfg):
    """Return a list of problems found in the settings (empty when fine)."""
    problems = []
    if cfg["profile"] not in ("S", "M", "G"):
        problems.append("profile must be S, M or G")
    if cfg["operating_model"] not in ("owned", "managed", "franchised"):
        problems.append("operating_model must be owned, managed or franchised")
    for t in cfg["triggers"]:
        if t not in ("T1", "T2", "T3", "T4", "T5"):
            problems.append("unknown trigger %s" % t)
    for s in ("D", "P", "J"):
        if s not in cfg["strength_weights"]:
            problems.append("strength_weights needs %s" % s)
    for lv in ("Baseline", "Enhanced"):
        if lv not in cfg["level_weights"]:
            problems.append("level_weights needs %s" % lv)
    for e in ("S", "M", "L"):
        if e not in cfg["effort_weights"] or cfg["effort_weights"][e] <= 0:
            problems.append("effort_weights needs a positive %s" % e)
    if not 0 <= cfg["met_threshold"] <= 4:
        problems.append("met_threshold must be 0 to 4")
    return problems
