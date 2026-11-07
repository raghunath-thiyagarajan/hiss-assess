"""Build dashboard.html: one self contained page with inline CSS and JavaScript.

The page template lives in dashboard_template.html next to this file. No external addresses, fonts or scripts are
used, so the page opens offline and on a phone. Tabs: overview, domains, standards, jurisdictions, gaps and roadmap.
Light and dark follow the system setting.
"""
import json
import os

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_template.html")


def dashboard_payload(res):
    """The parts of the results the page needs."""
    return {
        "property": res["property"], "input": {k: v for k, v in res["input"].items() if k != "assessment_file"},
        "assumptions": res["assumptions"], "overall": res["overall"],
        "applicability": {"total": res["applicability"]["total"], "applicable": res["applicability"]["applicable"]},
        "domains": res["domains"], "controls": res["controls"],
        "standard": {"frameworks": res["standard"]["frameworks"], "rows": res["standard"]["rows"],
                     "unknown_targets": res["standard"]["unknown_targets"]},
        "jurisdictions": {"summary": res["jurisdictions"]["summary"], "overall": res["jurisdictions"]["overall"],
                          "rows": res["jurisdictions"]["rows"], "out_of_scope": len(res["jurisdictions"]["out_of_scope"])},
        "gap": res["gap"], "roadmap": res["roadmap"],
        "sensitivity": {"roadmap_summary": res["sensitivity"]["roadmap_summary"],
                        "framework_summary": res["sensitivity"]["framework_summary"]},
        "hissrat": ({k: v for k, v in res["hissrat"].items() if k != "caps"} if res.get("hissrat") else None),
        "familyCoverage": res["family_coverage"], "author": res["author"],
    }


def render_dashboard(res):
    """Return the complete HTML text with the data embedded as JSON."""
    with open(TEMPLATE, encoding="utf-8") as fh:
        html = fh.read()
    payload = json.dumps(dashboard_payload(res), ensure_ascii=True)
    payload = payload.replace("</", "<\\/").replace("<!--", "<\\!--")
    return html.replace("__PAYLOAD__", payload)
