"""Load the HISS catalogue and check it against the schema contract.

The catalogue is a folder of plain files (see catalogue/SCHEMA.md):
controls.csv, crosswalk.csv, obligations.csv, profiles.json, realities.csv, family_map.csv and requirements.csv.

load_catalogue() only reads. validate_catalogue() returns errors and warnings and never raises,
so a caller can decide what to do. Run this file directly for a printed check:

    python src/catalogue.py [catalogue folder] [--full]

The --full flag adds the size checks from the design (76 to 84 controls, 4 to 6 per domain,
16 domains and at least three controls per hotel reality).
"""
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (CATALOGUE_DIR, CONFIG_DIR, DOMAIN_ORDER, domain_sort_key, read_csv, read_csv_header,  # noqa: E402
                    read_json, resolve_path, split_list)

CONTROL_FIELDS = ["control_id", "domain", "title", "objective", "requirement", "rationale", "level", "profiles",
                  "triggers", "owner_owned", "owner_managed", "owner_franchised", "realities", "evidence_expected",
                  "assessment_question", "c1_link", "basis"]
CROSSWALK_FIELDS = ["control_id", "framework", "target_id", "target_title", "strength", "source", "target_status", "note"]
OBLIGATION_FIELDS = ["obligation_id", "jurisdiction", "instrument", "provision", "summary", "hotel_trigger", "status",
                     "fact_ref", "control_ids"]
REALITY_FIELDS = ["reality_id", "name", "description"]
FAMILY_FIELDS = ["family_key", "family_name", "control_ids", "note"]
REQUIREMENT_FIELDS = ["req_id", "text", "c1_ref", "control_ids"]

FILES = {
    "controls": "controls.csv",
    "crosswalk": "crosswalk.csv",
    "obligations": "obligations.csv",
    "profiles": "profiles.json",
    "realities": "realities.csv",
    "families": "family_map.csv",
    "requirements": "requirements.csv",
}
FIELDS = {"controls": CONTROL_FIELDS, "crosswalk": CROSSWALK_FIELDS, "obligations": OBLIGATION_FIELDS,
          "realities": REALITY_FIELDS, "families": FAMILY_FIELDS, "requirements": REQUIREMENT_FIELDS}

FRAMEWORKS = ["ISO27001", "PCIDSS", "CSF", "CIS", "CCM", "SP1800-27", "HTNG"]
FRAMEWORK_NAMES = {
    "ISO27001": "ISO/IEC 27001:2022 Annex A",
    "PCIDSS": "PCI DSS v4.0.1",
    "CSF": "NIST CSF 2.0",
    "CIS": "CIS Controls v8.1",
    "CCM": "CSA CCM v4",
    "SP1800-27": "NIST SP 1800-27",
    "HTNG": "HTNG guidance",
}
STRENGTHS = ("D", "P", "J")
TARGET_STATUSES = ("VERIFIED", "SECONDARY", "NOT VERIFIED")
OBLIGATION_STATUSES = ("VERIFIED", "SECONDARY")
LEVELS = ("Baseline", "Enhanced")
PROFILES = ("S", "M", "G")
TRIGGERS = ("T1", "T2", "T3", "T4", "T5")
OWNERS = ("group", "property", "vendor", "franchisee")
BASES = ("sourced", "derived", "judgement")
REALITY_IDS = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
# Per control caps on crosswalk rows by framework (design section on the crosswalk model).
ROW_CAPS = {"ISO27001": 3, "PCIDSS": 2, "CSF": 2, "CIS": 2, "CCM": 1}

CONTROL_ID_RX = re.compile(r"^HISS-(F[1-6]|H(?:0[1-9]|10))-\d{2}$")
JURISDICTION_RX = re.compile(r"^[A-Z]{2,3}(-[A-Z0-9]{2,6})?$")


class CatalogueError(Exception):
    """Raised when catalogue files are missing or unreadable."""


def load_catalogue(path=None):
    """Read all catalogue files from a folder and add parsed list fields. No validation happens here."""
    folder = resolve_path(path) if path else CATALOGUE_DIR
    missing = [name for name in FILES.values() if not os.path.isfile(os.path.join(folder, name))]
    if missing:
        raise CatalogueError("catalogue folder %s is missing: %s" % (folder, ", ".join(missing)))
    cat = {"path": folder, "headers": {}}
    for key, name in FILES.items():
        full = os.path.join(folder, name)
        if name.endswith(".json"):
            cat[key] = read_json(full)
        else:
            cat["headers"][key] = read_csv_header(full)
            cat[key] = read_csv(full)
    for c in cat["controls"]:
        c["profile_list"] = split_list(c.get("profiles"))
        c["trigger_list"] = split_list(c.get("triggers"))
        c["reality_list"] = split_list(c.get("realities"))
        c["evidence_list"] = split_list(c.get("evidence_expected"))
    for o in cat["obligations"]:
        o["control_list"] = split_list(o.get("control_ids"))
    for f in cat["families"]:
        f["control_list"] = split_list(f.get("control_ids"))
    for r in cat["requirements"]:
        r["control_list"] = split_list(r.get("control_ids"))
    cat["control_by_id"] = {}
    for c in cat["controls"]:
        cat["control_by_id"].setdefault(c["control_id"], c)
    return cat


def load_domain_names(cat=None):
    """Domain code to name. profiles.json may carry a domains object that overrides config/domains.json."""
    names = {}
    path = os.path.join(CONFIG_DIR, "domains.json")
    if os.path.isfile(path):
        names.update(read_json(path))
    if cat and isinstance(cat.get("profiles"), dict):
        extra = cat["profiles"].get("domains")
        if isinstance(extra, dict):
            names.update({k: (v if isinstance(v, str) else v.get("name", k)) for k, v in extra.items()})
    return names


def load_clause_universe(cat=None):
    """Clause lists per framework, used only to list clauses that no control reaches.

    A file framework_clauses.csv in the catalogue folder (framework, target_id, target_title) wins when present.
    Otherwise config/framework_clauses.json is used. Returns {framework: [{"id", "title"}]} or an empty dict.
    """
    if cat:
        csv_path = os.path.join(cat["path"], "framework_clauses.csv")
        if os.path.isfile(csv_path):
            out = defaultdict(list)
            for r in read_csv(csv_path):
                out[r["framework"]].append({"id": r["target_id"], "title": r.get("target_title", "")})
            return dict(out)
    path = os.path.join(CONFIG_DIR, "framework_clauses.json")
    if os.path.isfile(path):
        return read_json(path).get("frameworks", {})
    return {}


def ordered_domains(controls):
    return sorted({c["domain"] for c in controls}, key=domain_sort_key)


def validate_catalogue(cat, full=False):
    """Return {"errors": [...], "warnings": [...]}. Errors break the contract; warnings are quality notes."""
    errors, warnings = [], []
    err, warn = errors.append, warnings.append

    # Headers
    for key, fields in FIELDS.items():
        header = cat.get("headers", {}).get(key)
        if header is None:
            continue
        missing = [f for f in fields if f not in header]
        if missing:
            err("%s: missing columns %s" % (FILES[key], ", ".join(missing)))
    if not isinstance(cat.get("profiles"), dict) or "profiles" not in cat["profiles"]:
        err("profiles.json: no profiles object")
    else:
        for p in PROFILES:
            if p not in cat["profiles"]["profiles"]:
                err("profiles.json: profile %s is not defined" % p)
        if "triggers" not in cat["profiles"]:
            err("profiles.json: no triggers object")

    controls = cat["controls"]
    ids = [c.get("control_id", "") for c in controls]
    known_controls = set(ids)
    realities = {r.get("reality_id", "") for r in cat["realities"]}

    # Controls
    seen = set()
    for n, c in enumerate(controls, 2):
        cid = c.get("control_id", "")
        where = "controls.csv row %d (%s)" % (n, cid)
        if cid in seen:
            err("%s: duplicate control_id" % where)
        seen.add(cid)
        if not CONTROL_ID_RX.match(cid):
            err("%s: control_id does not match HISS-<domain>-<nn>" % where)
        elif cid.split("-")[1] != c.get("domain"):
            err("%s: domain %s does not match the control_id" % (where, c.get("domain")))
        for f in ("title", "objective", "requirement", "rationale", "assessment_question"):
            if not (c.get(f) or "").strip():
                err("%s: %s is empty" % (where, f))
        level = c.get("level")
        if level not in LEVELS:
            err("%s: level must be Baseline or Enhanced" % where)
        bad = [p for p in c["profile_list"] if p not in PROFILES]
        if bad or not c["profile_list"]:
            err("%s: profiles must be a list drawn from S;M;G" % where)
        if level == "Baseline" and set(c["profile_list"]) != set(PROFILES):
            err("%s: a Baseline control applies to S;M;G" % where)
        if level == "Enhanced" and "S" in c["profile_list"]:
            warn("%s: an Enhanced control lists profile S (it applies to S without a trigger)" % where)
        bad = [t for t in c["trigger_list"] if t not in TRIGGERS]
        if bad:
            err("%s: unknown trigger %s" % (where, ", ".join(bad)))
        for f in ("owner_owned", "owner_managed", "owner_franchised"):
            if c.get(f) not in OWNERS:
                err("%s: %s must be one of %s" % (where, f, "/".join(OWNERS)))
        bad = [r for r in c["reality_list"] if r not in realities]
        if bad or not c["reality_list"]:
            err("%s: realities must list ids defined in realities.csv" % where)
        if len(c["evidence_list"]) < 2:
            err("%s: evidence_expected needs at least two artefacts" % where)
        if c.get("basis") not in BASES:
            err("%s: basis must be sourced, derived or judgement" % where)
        if not (c.get("c1_link") or "").strip():
            warn("%s: c1_link is empty" % where)

    # Crosswalk
    per_control = defaultdict(Counter)
    frameworks_of = defaultdict(set)
    seen_rows = set()
    for n, x in enumerate(cat["crosswalk"], 2):
        cid = x.get("control_id", "")
        where = "crosswalk.csv row %d (%s)" % (n, cid)
        if cid not in known_controls:
            err("%s: control_id is not in controls.csv" % where)
        if x.get("framework") not in FRAMEWORKS:
            err("%s: unknown framework %s" % (where, x.get("framework")))
        if x.get("strength") not in STRENGTHS:
            err("%s: strength must be D, P or J" % where)
        if x.get("strength") == "D" and not (x.get("source") or "").strip():
            err("%s: a D row needs a named source" % where)
        if x.get("target_status") not in TARGET_STATUSES:
            err("%s: target_status must be VERIFIED, SECONDARY or NOT VERIFIED" % where)
        if x.get("strength") == "D" and x.get("target_status") not in (None, "VERIFIED"):
            warn("%s: a D row should point to a VERIFIED target" % where)
        if not (x.get("target_id") or "").strip():
            err("%s: target_id is empty" % where)
        key = (cid, x.get("framework"), x.get("target_id"))
        if key in seen_rows:
            err("%s: duplicate control, framework and target" % where)
        seen_rows.add(key)
        per_control[cid][x.get("framework")] += 1
        frameworks_of[cid].add(x.get("framework"))
    used_triggers = {t for c in controls for t in c["trigger_list"]}
    for t in TRIGGERS:
        if t not in used_triggers:
            warn("trigger %s is used by no control, so switching it on changes nothing" % t)
    for cid in ids:
        for fw, cap in ROW_CAPS.items():
            if per_control[cid][fw] > cap:
                warn("%s has %d %s rows (cap %d)" % (cid, per_control[cid][fw], fw, cap))
        for fw in ("ISO27001", "CSF", "CIS"):
            if fw not in frameworks_of[cid]:
                warn("%s has no %s row" % (cid, fw))

    # Obligations
    seen = set()
    for n, o in enumerate(cat["obligations"], 2):
        oid = o.get("obligation_id", "")
        where = "obligations.csv row %d (%s)" % (n, oid)
        if oid in seen:
            err("%s: duplicate obligation_id" % where)
        seen.add(oid)
        if not JURISDICTION_RX.match(o.get("jurisdiction", "")):
            err("%s: jurisdiction tag %r looks wrong" % (where, o.get("jurisdiction")))
        if o.get("status") not in OBLIGATION_STATUSES:
            err("%s: status must be VERIFIED or SECONDARY" % where)
        if not o["control_list"]:
            warn("%s: no linked controls" % where)
        for cid in o["control_list"]:
            if cid not in known_controls:
                err("%s: linked control %s is not in controls.csv" % (where, cid))
        if not (o.get("fact_ref") or "").strip():
            warn("%s: fact_ref is empty" % where)

    # Families, requirements, realities
    for n, f in enumerate(cat["families"], 2):
        where = "family_map.csv row %d (%s)" % (n, f.get("family_key"))
        if not f["control_list"]:
            err("%s: no controls" % where)
        for cid in f["control_list"]:
            if cid not in known_controls:
                err("%s: control %s is not in controls.csv" % (where, cid))
    if len(cat["families"]) != 12:
        warn("family_map.csv has %d families (the Capstone 1 case has 12)" % len(cat["families"]))
    for n, r in enumerate(cat["requirements"], 2):
        where = "requirements.csv row %d (%s)" % (n, r.get("req_id"))
        if not r["control_list"]:
            warn("%s: no linked controls (counts as absent under HISS)" % where)
        for cid in r["control_list"]:
            if cid not in known_controls:
                err("%s: control %s is not in controls.csv" % (where, cid))

    if full:
        n = len(controls)
        if not 76 <= n <= 84:
            err("catalogue has %d controls (the design allows 76 to 84)" % n)
        by_dom = Counter(c["domain"] for c in controls)
        for d in DOMAIN_ORDER:
            if d not in by_dom:
                err("domain %s has no controls" % d)
            elif not 4 <= by_dom[d] <= 6:
                err("domain %s has %d controls (4 to 6 allowed)" % (d, by_dom[d]))
        for rid in REALITY_IDS:
            k = sum(1 for c in controls if rid in c["reality_list"])
            if k < 3:
                err("reality %s is addressed by %d controls (3 needed)" % (rid, k))
        if not 30 <= len(cat["obligations"]) <= 40:
            warn("obligations.csv has %d rows (30 to 40 expected)" % len(cat["obligations"]))
    return {"errors": errors, "warnings": warnings}


def catalogue_stats(cat):
    """Counts used in the catalogue statistics table: controls per domain, level split, strength split and so on."""
    controls = cat["controls"]
    by_domain = Counter(c["domain"] for c in controls)
    strengths = Counter(x["strength"] for x in cat["crosswalk"])
    by_framework = {}
    for fw in FRAMEWORKS:
        rows = [x for x in cat["crosswalk"] if x["framework"] == fw]
        by_framework[fw] = {"rows": len(rows),
                            "D": sum(1 for x in rows if x["strength"] == "D"),
                            "P": sum(1 for x in rows if x["strength"] == "P"),
                            "J": sum(1 for x in rows if x["strength"] == "J")}
    oblig = Counter(o["jurisdiction"] for o in cat["obligations"])
    status = Counter(o["status"] for o in cat["obligations"])
    reality_cover = {r["reality_id"]: sum(1 for c in controls if r["reality_id"] in c["reality_list"])
                     for r in cat["realities"]}
    return {
        "controls": len(controls),
        "controls_per_domain": {d: by_domain[d] for d in sorted(by_domain, key=domain_sort_key)},
        "level_split": dict(Counter(c["level"] for c in controls)),
        "basis_split": dict(Counter(c["basis"] for c in controls)),
        "crosswalk_rows": len(cat["crosswalk"]),
        "strength_split": {s: strengths.get(s, 0) for s in STRENGTHS},
        "rows_by_framework": by_framework,
        "obligations": len(cat["obligations"]),
        "obligations_by_jurisdiction": dict(sorted(oblig.items())),
        "obligations_by_status": dict(status),
        "controls_per_reality": reality_cover,
        "families": len(cat["families"]),
        "requirements": len(cat["requirements"]),
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    full = "--full" in argv
    args = [a for a in argv if not a.startswith("--")]
    cat = load_catalogue(args[0] if args else None)
    res = validate_catalogue(cat, full=full)
    stats = catalogue_stats(cat)
    print("Catalogue folder:", cat["path"])
    print("Controls %d, crosswalk rows %d, obligations %d, families %d, requirements %d" % (
        stats["controls"], stats["crosswalk_rows"], stats["obligations"], stats["families"], stats["requirements"]))
    for w in res["warnings"]:
        print("warning:", w)
    for e in res["errors"]:
        print("error:", e)
    print("%d errors, %d warnings" % (len(res["errors"]), len(res["warnings"])))
    return 1 if res["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
