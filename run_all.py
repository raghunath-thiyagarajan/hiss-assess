#!/usr/bin/env python3
"""Run HISS-Assess for one or more properties with one command.

    python run_all.py --property NAME --config config/assessment_config.json

Steps: load and check the catalogue, write docs/HISS_Standard_v1.md, read inputs/assessment_<NAME>.csv
(a blank one is written if it is missing), read optional HISS-RAT files from inputs/hissrat/, then score and
write all outputs to outputs/. With several property names each property gets its own folder under outputs/
and a group summary is written next to them.

Useful options:
    --catalogue DIR     catalogue folder (default catalogue/)
    --inputs-dir DIR    folder with the assessment files (default inputs/)
    --hissrat-dir DIR   anonymised HISS-RAT files (default inputs/hissrat when it exists)
    --no-hissrat        ignore HISS-RAT files
    --out-dir DIR       output folder (default outputs/)
    --docs-dir DIR      folder for HISS_Standard_v1.md (default docs/)
    --no-standard       do not write the standard
    --template-only     only write the blank questionnaire for each property
    --allow-errors      continue even when the catalogue check reports errors
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

import applicability  # noqa: E402
import catalogue  # noqa: E402
import gap  # noqa: E402
import ingest_hissrat  # noqa: E402
import pipeline  # noqa: E402
import render_standard  # noqa: E402
import report  # noqa: E402
import score  # noqa: E402
import settings  # noqa: E402
import template  # noqa: E402
from common import (CATALOGUE_DIR, DOCS_DIR, INPUTS_DIR, OUT_DIR, read_csv, read_json,  # noqa: E402
                    resolve_path, write_csv, write_json)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--property", nargs="+", required=True, help="property name, matching inputs/assessment_<NAME>.csv")
    ap.add_argument("--config", default=os.path.join("config", "assessment_config.json"))
    ap.add_argument("--catalogue", default=None)
    ap.add_argument("--inputs-dir", default=None)
    ap.add_argument("--hissrat-dir", default=None)
    ap.add_argument("--no-hissrat", action="store_true")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--docs-dir", default=None)
    ap.add_argument("--no-standard", action="store_true")
    ap.add_argument("--template-only", action="store_true")
    ap.add_argument("--allow-errors", action="store_true")
    return ap.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    cat_dir = resolve_path(a.catalogue) if a.catalogue else CATALOGUE_DIR
    inputs_dir = resolve_path(a.inputs_dir) if a.inputs_dir else INPUTS_DIR
    out_dir = resolve_path(a.out_dir) if a.out_dir else OUT_DIR
    docs_dir = resolve_path(a.docs_dir) if a.docs_dir else DOCS_DIR

    try:
        cat = catalogue.load_catalogue(cat_dir)
    except catalogue.CatalogueError as e:
        print("Cannot load the catalogue:", e)
        return 2
    check = catalogue.validate_catalogue(cat)
    for w in check["warnings"][:15]:
        print("catalogue warning:", w)
    if len(check["warnings"]) > 15:
        print("catalogue warning: %d more warnings (run python src/catalogue.py for the full list)" % (len(check["warnings"]) - 15))
    for e in check["errors"][:30]:
        print("catalogue error:", e)
    if check["errors"]:
        print("%d catalogue errors." % len(check["errors"]))
        if not a.allow_errors:
            print("Stopping. Fix the catalogue or use --allow-errors to continue anyway.")
            return 2
    universe = catalogue.load_clause_universe(cat)
    domain_names = catalogue.load_domain_names(cat)

    if not a.no_standard and not a.template_only:
        out = render_standard.write_standard(cat, os.path.join(docs_dir, "HISS_Standard_v1.md"), domain_names)
        print("Wrote", shown(out))

    try:
        raw_cfg = read_json(resolve_path(a.config))
    except (OSError, ValueError) as e:
        print("Cannot read the config file:", e)
        return 2

    hissrat = None
    if not a.no_hissrat and not a.template_only:
        hdir = resolve_path(a.hissrat_dir) if a.hissrat_dir else os.path.join(inputs_dir, "hissrat")
        if os.path.isfile(os.path.join(hdir, "systems_normalised.csv")):
            role_tier = (raw_cfg.get("hissrat") or {}).get("role_tier", {})
            hissrat = ingest_hissrat.load_hissrat(hdir, role_tier)
            print("Read HISS-RAT files: %d systems" % len(hissrat["systems"]))
        elif a.hissrat_dir:
            print("No systems_normalised.csv found in the HISS-RAT folder you gave.")
            return 2
    families = ingest_hissrat.load_family_patterns() if hissrat else None

    iso_manual, iso_notes = None, []
    mpath = os.path.join(inputs_dir, "iso_only_manual.csv")
    if os.path.isfile(mpath) and not a.template_only:
        iso_manual, iso_notes = gap.parse_iso_manual(read_csv(mpath), {r["req_id"] for r in cat["requirements"]})
        print("Read hand classification for %d requirements from iso_only_manual.csv" % len(iso_manual))
        for n in iso_notes:
            print(n)

    results, missing = [], []
    multi = len(a.property) > 1
    for name in a.property:
        cfg = settings.property_settings(raw_cfg, name)
        problems = settings.check_settings(cfg)
        if problems:
            print("Settings problems for %s: %s" % (name, "; ".join(problems)))
            return 2
        app_rows = applicability.filter_controls(cat["controls"], cfg)
        apath = os.path.join(inputs_dir, "assessment_%s.csv" % name)
        if a.template_only or not os.path.isfile(apath):
            if os.path.isfile(apath):
                print("%s already exists and was left as it is." % os.path.basename(apath))
            else:
                p1, p2 = template.write_template(apath, cat["control_by_id"], app_rows)
                print("Wrote blank questionnaire %s and %s" % (os.path.basename(p1), os.path.basename(p2)))
                missing.append(name)
            continue
        answers, notes = template.read_assessment(apath, cat["control_by_id"], applicability.applicable_ids(app_rows))
        for n in notes:
            print("%s: %s" % (name, n))
        res = pipeline.run_property(cat, cfg, answers, hissrat=hissrat, universe=universe, domain_names=domain_names,
                                    families=families, input_problems=notes + iso_notes, assessment_name=os.path.basename(apath), iso_manual=iso_manual)
        target = os.path.join(out_dir, name) if multi else out_dir
        report.write_outputs(res, target)
        results.append(res)
        summarise(res, target)

    if multi and results and not missing:
        group = score.group_maturity([{"property": r["property"]["name"], "overall": r["overall"], "domains": r["domains"]}
                                      for r in results])
        rows = []
        for r in results:
            row = {"property": r["property"]["name"], "profile": r["property"]["profile"],
                   "controls": r["overall"]["controls"], "maturity_pct": r["overall"]["maturity_pct"],
                   "met_pct": r["overall"]["met_pct"]}
            for d, vals in group["domain_matrix"].items():
                row[d] = vals.get(r["property"]["name"], "")
            rows.append(row)
        fields = ["property", "profile", "controls", "maturity_pct", "met_pct"] + list(group["domain_matrix"])
        write_csv(os.path.join(out_dir, "group_summary.csv"), rows, fields)
        write_json(os.path.join(out_dir, "group_results.json"), group)
        print("Group maturity %.1f percent over %d properties. Wrote group_summary.csv and group_results.json" % (
            group["group_maturity_pct"], len(results)))
    if missing:
        print("Fill in the blank questionnaire(s) for %s and run the command again." % ", ".join(missing))
        return 2
    return 0


def summarise(res, target):
    o = res["overall"]
    print("\n%s: %d of %d controls apply. Mean maturity %.2f of 4 (%.1f percent). Met %d (%.1f percent)." % (
        res["property"]["name"], res["applicability"]["applicable"], res["applicability"]["total"], o["mean_maturity"],
        o["maturity_pct"], o["met"], o["met_pct"]))
    for f in res["standard"]["frameworks"]:
        u = f["universe_known"]
        print("  %-28s source backed %s, indicative %s" % (
            f["name"], _p(f["source_backed_pct_universe"] if u else f["source_backed_pct_reached"]),
            _p(f["indicative_pct_universe"] if u else f["indicative_pct_reached"])))
    s = res["jurisdictions"]["overall"]
    print("  Jurisdictions: %d obligations scored, readiness %s, %d tracked" % (
        s["obligations_scored"], _p(s["readiness_pct"]), s["tracking_n"]))
    print("  Roadmap: " + ", ".join("%s %d" % (w["label"].split(" (")[0], w["items"]) for w in res["roadmap"]["waves"]))
    print("  Outputs written to", shown(target))


def shown(path):
    """Path as shown on screen: relative to the toolkit folder when inside it, otherwise the last two parts only."""
    if path.startswith(ROOT + os.sep):
        return os.path.relpath(path, ROOT)
    return os.path.join(os.path.basename(os.path.dirname(path)), os.path.basename(path))


def _p(v):
    return "n/a" if v in (None, "") else "%s%%" % v


if __name__ == "__main__":
    sys.exit(main())
