"""Turn anonymised HISS-RAT findings into maturity caps on HISS controls.

Input folder (inputs/hissrat/), all produced by the Capstone 1 toolkit and anonymised:
  systems_normalised.csv   one row per system (required)
  findings_normalised.csv  one row per plugin per system (optional; without it the plugins_low_plus column is used)
  risk_register.csv        adds the Capstone 1 tier of each system (optional; without it the role tier from the config is used)

Rule (assumed, register A25): a Critical or High finding on an in scope system caps a control linked to its
finding family at maturity 1. A Medium finding caps at 2. Low findings set no cap. The cap lowers the self
assessed maturity and never raises it. Family to control links come from family_map.csv.
Role rule (assumed, A25): the control must also sit in a domain that the role of the affected system can influence,
as listed in config/system_roles.json. Foundation domains F1 to F6 are allowed for every role. A system with an
unknown role falls back to the earlier behaviour and is reported.
Nothing in this module reads raw scan files, addresses or host names.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CONFIG_DIR, MAX_MATURITY, read_csv, read_json  # noqa: E402

SEVERITY_RANK = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "Info": 0}
LOW_PLUS = ("Critical", "High", "Medium", "Low")


def load_family_patterns(path=None):
    """Read finding family patterns. Accepts the file shipped in config/ or a Capstone 1 standards map."""
    data = read_json(path or os.path.join(CONFIG_DIR, "family_patterns.json"))
    fams = []
    for f in data["families"]:
        fams.append({"key": f["key"], "label": f.get("label", f["key"]), "patterns": list(f["patterns"]),
                     "_rx": [re.compile(p, re.I) for p in f["patterns"]]})
    return fams


def classify_finding(plugin_name, families):
    """Family key for a plugin name. An empty string means no pattern matches."""
    for f in families:
        if any(rx.search(plugin_name) for rx in f["_rx"]):
            return f["key"]
    return ""


def parse_plugin_list(text):
    """Parse the plugins_low_plus cell: 'Severity:Name | Severity:Name'. Returns (severity, name) pairs."""
    out = []
    for item in (text or "").split(" | "):
        sev, _, name = item.partition(":")
        sev = sev.strip()
        if sev in SEVERITY_RANK and name.strip():
            out.append((sev, name.strip()))
    return out


def load_hissrat(folder, role_tier=None):
    """Read systems and Low or above findings from a HISS-RAT output folder.

    Returns {"systems": [...], "findings": [...], "findings_source": text, "tier_source": text}.
    Each system has system_id, property, role_key, role_group and tier (an integer or None).
    Each finding has system_id, property, plugin_name and severity.
    """
    spath = os.path.join(folder, "systems_normalised.csv")
    if not os.path.isfile(spath):
        raise FileNotFoundError("systems_normalised.csv not found in %s" % folder)
    sys_rows = read_csv(spath)
    tiers, tier_source = {}, "none"
    rpath = os.path.join(folder, "risk_register.csv")
    if os.path.isfile(rpath):
        for r in read_csv(rpath):
            try:
                tiers[r["system_id"]] = int(r["tier"])
            except (KeyError, ValueError):
                pass
        tier_source = "risk_register.csv"
    role_tier = role_tier or {}
    systems = []
    for r in sys_rows:
        tier = tiers.get(r["system_id"])
        if tier is None and r.get("role_key") in role_tier:
            tier = int(role_tier[r["role_key"]])
            tier_source = tier_source if tier_source != "none" else "role tier in config"
        systems.append({"system_id": r["system_id"], "property": r.get("property", ""), "role_key": r.get("role_key", ""),
                        "role": r.get("role", ""), "role_group": r.get("role_group", ""), "tier": tier})
    findings, source = [], ""
    fpath = os.path.join(folder, "findings_normalised.csv")
    if os.path.isfile(fpath):
        for r in read_csv(fpath):
            if r.get("severity") in LOW_PLUS:
                findings.append({"system_id": r["system_id"], "property": r.get("property", ""),
                                 "plugin_name": r["plugin_name"], "severity": r["severity"]})
        source = "findings_normalised.csv"
    else:
        for r in sys_rows:
            for sev, name in parse_plugin_list(r.get("plugins_low_plus", "")):
                findings.append({"system_id": r["system_id"], "property": r.get("property", ""),
                                 "plugin_name": name, "severity": sev})
        source = "plugins_low_plus column of systems_normalised.csv"
    return {"systems": systems, "findings": findings, "findings_source": source, "tier_source": tier_source}


def classify_findings(findings, families):
    """Add a family key to each finding (in place) and return the list."""
    for f in findings:
        f["family"] = classify_finding(f["plugin_name"], families)
    return findings


def summarise(systems, findings, families):
    """Totals that should reproduce the Capstone 1 counts: systems, Low or above findings and families."""
    by_sev = {s: 0 for s in LOW_PLUS}
    for f in findings:
        by_sev[f["severity"]] += 1
    keys = {f["family"] for f in findings if f.get("family")}
    return {
        "systems": len(systems),
        "findings_low_plus": len(findings),
        "by_severity": by_sev,
        "families_defined": len(families),
        "families_found": len(keys),
        "findings_without_family": sum(1 for f in findings if not f.get("family")),
        "by_family": {k: sum(1 for f in findings if f.get("family") == k) for k in sorted(keys)},
    }


def select_scope(systems, properties):
    """Systems of the properties being assessed. properties is a list of codes, 'all' or None."""
    if properties in (None, "all"):
        return list(systems)
    if isinstance(properties, str):
        properties = [properties]
    wanted = {p.upper() for p in properties}
    if "ALL" in wanted:
        return list(systems)
    return [s for s in systems if s["property"].upper() in wanted]


def family_to_controls(family_rows):
    """family_key to list of control ids from family_map.csv rows (rows may carry control_list or control_ids)."""
    out = {}
    for f in family_rows:
        ids = f.get("control_list")
        if ids is None:
            ids = [x.strip() for x in (f.get("control_ids") or "").split(";") if x.strip()]
        out[f["family_key"]] = list(ids)
    return out


def family_coverage(family_rows, control_by_id):
    """Check that each finding family reaches at least one catalogue control (design check V1)."""
    mapping = family_to_controls(family_rows)
    covered = {k: [c for c in ids if c in control_by_id] for k, ids in mapping.items()}
    return {"families": len(mapping), "mapped": sum(1 for v in covered.values() if v),
            "unmapped_families": sorted(k for k, v in covered.items() if not v), "controls": covered}


def load_system_roles(path=None):
    """Read the role to domain table (config/system_roles.json by default)."""
    return read_json(path or os.path.join(CONFIG_DIR, "system_roles.json"))


def allowed_domains(system, roles):
    """Domains that the role of a system can influence, or None when the role is not listed."""
    cls = roles.get("role_keys", {}).get(system.get("role_key", "")) or roles.get("role_labels", {}).get(system.get("role", ""))
    if not cls or cls not in roles.get("role_classes", {}):
        return None
    return set(roles["role_classes"][cls]["domains"]) | set(roles.get("foundation_domains", []))


def derive_caps(findings, systems_in_scope, fam_controls, cap_rules, control_domain=None, system_roles=None):
    """Maturity caps per control from in scope findings (see derive_caps_ex for the notes)."""
    return derive_caps_ex(findings, systems_in_scope, fam_controls, cap_rules, control_domain, system_roles)[0]


def derive_caps_ex(findings, systems_in_scope, fam_controls, cap_rules, control_domain=None, system_roles=None):
    """Maturity caps per control from in scope findings, with notes on the role rule.

    cap_rules maps severity to a cap, for example {"Critical": 1, "High": 1, "Medium": 2}.
    When both control_domain (control id to domain) and system_roles are given the role rule applies.
    Returns (caps, notes). caps is {control_id: {"cap", "severity", "systems", "families", "tiers", "findings", "reasons"}}.
    notes is {"role_rule": bool, "unknown_roles": [...], "skipped": number of control applications the role rule removed}.
    """
    scope = {s["system_id"]: s for s in systems_in_scope}
    use_roles = bool(system_roles) and control_domain is not None
    unknown, skipped = set(), 0
    caps = {}
    ordered = sorted((f for f in findings if f["system_id"] in scope and f.get("family") in fam_controls),
                     key=lambda f: (-SEVERITY_RANK[f["severity"]], f["system_id"], f["plugin_name"]))
    for f in ordered:
        cap = cap_rules.get(f["severity"])
        if cap is None:
            continue
        allowed = None
        if use_roles:
            allowed = allowed_domains(scope[f["system_id"]], system_roles)
            if allowed is None:
                unknown.add(scope[f["system_id"]].get("role_key") or scope[f["system_id"]].get("role") or "blank role")
        for cid in fam_controls[f["family"]]:
            if allowed is not None and control_domain.get(cid) not in allowed:
                skipped += 1
                continue
            e = caps.setdefault(cid, {"cap": MAX_MATURITY, "severity": f["severity"], "systems": [], "families": [],
                                      "tiers": [], "findings": 0, "reasons": []})
            if cap < e["cap"]:
                e["cap"] = cap
            if SEVERITY_RANK[f["severity"]] > SEVERITY_RANK[e["severity"]]:
                e["severity"] = f["severity"]
            sid = f["system_id"]
            if sid not in e["systems"]:
                e["systems"].append(sid)
                tier = scope[sid]["tier"]
                if tier is not None:
                    e["tiers"].append(tier)
            if f["family"] not in e["families"]:
                e["families"].append(f["family"])
            e["findings"] += 1
            reason = "%s on %s (%s)" % (f["severity"], sid, f["family"])
            if reason not in e["reasons"]:
                e["reasons"].append(reason)
    for e in caps.values():
        e["reasons"] = e["reasons"][:3]
        e["systems"].sort()
    return caps, {"role_rule": use_roles, "unknown_roles": sorted(unknown), "skipped": skipped}


def apply_cap(maturity, cap):
    """Effective maturity after a cap. A missing cap leaves the value as it is."""
    if maturity is None or cap is None:
        return maturity
    return min(maturity, cap)
