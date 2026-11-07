"""One assessment run for one property, as a pure function.

run_property() takes loaded data (catalogue, settings, answers and optional HISS-RAT data) and returns a results dict.
It does not read or write files and it keeps no absolute paths in the result.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import applicability  # noqa: E402
import gap  # noqa: E402
import ingest_hissrat  # noqa: E402
import roadmap  # noqa: E402
import score  # noqa: E402
import sensitivity  # noqa: E402
from catalogue import FRAMEWORK_NAMES, catalogue_stats, load_domain_names  # noqa: E402
from common import AUTHOR  # noqa: E402

ASSUMED_NOTE = ("Weights, caps, effort sizes, wave cut offs, profile choices and trigger choices are assumed values "
                "(register A20 to A31). They were not measured or validated.")


def run_property(cat, cfg, answers, hissrat=None, universe=None, domain_names=None, families=None,
                 input_problems=None, assessment_name="", iso_manual=None, system_roles=None):
    """Run the whole assessment and return the results dict."""
    domain_names = domain_names if domain_names is not None else load_domain_names(cat)
    controls_by_id = cat["control_by_id"]
    problems = list(input_problems or [])

    app_rows = applicability.filter_controls(cat["controls"], cfg)

    caps, ingest_info = {}, None
    fam_controls = ingest_hissrat.family_to_controls(cat["families"])
    coverage = ingest_hissrat.family_coverage(cat["families"], controls_by_id)
    if hissrat:
        fams = families if families is not None else ingest_hissrat.load_family_patterns()
        findings = ingest_hissrat.classify_findings(hissrat["findings"], fams)
        props = cfg["hissrat"].get("properties") or [cfg["property"]]
        scope = ingest_hissrat.select_scope(hissrat["systems"], props)
        if not scope:
            problems.append("no HISS-RAT systems matched property %s" % cfg["property"])
        role_aware = cfg["hissrat"].get("role_aware", True)
        roles = (system_roles if system_roles is not None else ingest_hissrat.load_system_roles()) if role_aware else None
        control_domain = {c["control_id"]: c["domain"] for c in cat["controls"]}
        caps, notes = ingest_hissrat.derive_caps_ex(findings, scope, fam_controls, cfg["finding_caps"],
                                                    control_domain, roles)
        if notes["unknown_roles"]:
            problems.append("HISS-RAT role(s) not listed in system_roles.json, so their findings cap every linked control "
                            "(earlier behaviour): %s" % ", ".join(notes["unknown_roles"]))
        # A cap can only act on a control that applies to this property.
        applicable = set(applicability.applicable_ids(app_rows))
        caps = {k: v for k, v in caps.items() if k in applicable}
        ingest_info = {
            "findings_source": hissrat["findings_source"], "tier_source": hissrat["tier_source"],
            "all_systems": ingest_hissrat.summarise(hissrat["systems"], findings, fams),
            "in_scope_systems": len(scope),
            "in_scope_findings": sum(1 for f in findings if f["system_id"] in {s["system_id"] for s in scope}),
            "controls_with_cap": len(caps),
            "role_rule": {"enabled": notes["role_rule"], "unknown_roles": notes["unknown_roles"],
                          "cap_applications_skipped": notes["skipped"]},
            "caps": {k: {"cap": v["cap"], "severity": v["severity"], "findings": v["findings"],
                         "systems": v["systems"], "families": v["families"], "reasons": v["reasons"]}
                     for k, v in sorted(caps.items())},
        }

    control_rows = score.score_controls(app_rows, controls_by_id, answers, caps, cfg)
    dom_rows = score.domain_scores(control_rows, domain_names)
    overall = score.property_score(control_rows, dom_rows)
    standard = score.standard_view(control_rows, cat["crosswalk"], cfg, universe)
    for f in standard["frameworks"]:
        f["name"] = FRAMEWORK_NAMES.get(f["framework"], f["framework"])
    juris = score.jurisdiction_readiness(cat["obligations"], control_rows, cfg)
    gaps = gap.build_gap(control_rows, standard, juris, cat, cfg, domain_names, iso_manual)
    items = roadmap.build_roadmap(control_rows, controls_by_id, caps, cfg)
    waves = roadmap.wave_summary(items, cfg)
    wave_sens = roadmap.wave_cutoff_sensitivity(items, cfg)
    if ingest_info is not None:
        ingest_info["controls_capped"] = overall["capped_by_scan"]
    sens_road = sensitivity.roadmap_sensitivity(control_rows, controls_by_id, caps, cfg)
    sens_fw = sensitivity.framework_sensitivity(control_rows, cat["crosswalk"], cfg, universe)

    answered = sum(1 for r in control_rows if r["answered"] == "yes")
    unanswered = len(control_rows) - answered
    if unanswered:
        problems.append("%d applicable controls are unanswered and count as maturity %d" % (unanswered, cfg["unanswered_as"]))

    return {
        "toolkit": "HISS-Assess",
        "author": AUTHOR,
        "property": {
            "name": cfg["property"], "label": cfg["label"], "profile": cfg["profile"],
            "operating_model": cfg["operating_model"], "triggers": list(cfg["triggers"]),
            "jurisdictions": dict(cfg["jurisdictions"]),
        },
        "input": {
            "status": cfg["input_status"], "tag": cfg["input_tag"], "assessment_file": assessment_name,
            "answered": answered, "applicable": len(control_rows), "problems": problems,
        },
        "assumptions": {
            "note": ASSUMED_NOTE,
            "met_threshold": cfg["met_threshold"], "target_maturity": cfg["target_maturity"],
            "strength_weights": cfg["strength_weights"], "finding_caps": cfg["finding_caps"],
            "level_weights": cfg["level_weights"], "tier_weights": {str(k): v for k, v in cfg["tier_weights"].items()},
            "effort_weights": cfg["effort_weights"], "waves": cfg["waves"],
        },
        "catalogue": catalogue_stats(cat),
        "hissrat": ingest_info,
        "family_coverage": {k: v for k, v in coverage.items() if k != "controls"},
        "applicability": {"total": len(app_rows), "applicable": len(control_rows), "rows": app_rows},
        "overall": overall,
        "domains": dom_rows,
        "controls": control_rows,
        "standard": standard,
        "jurisdictions": juris,
        "gap": gaps,
        "roadmap": {"items": roadmap.public_items(items), "waves": waves, "wave_sensitivity": wave_sens},
        "sensitivity": {
            "roadmap_rows": sens_road, "framework_rows": sens_fw,
            "roadmap_summary": sensitivity.summarise(sens_road, "domain_rho"),
            "framework_summary": sensitivity.summarise(sens_fw, "framework_rho"),
            "note": "Each weight moved by 20 percent up and down in turn. Spearman rho compares rankings with the base run.",
        },
    }
