"""Shared helpers for the HISS-Assess tests (standard library only, offline).

Importing this module puts src/ on the path and stops Python from writing bytecode,
so a test run leaves src/ and catalogue/ exactly as they were.
"""
import copy
import json
import os
import sys

sys.dont_write_bytecode = True

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS_DIR)
SRC_DIR = os.path.join(ROOT, "src")
CATALOGUE_DIR = os.path.join(ROOT, "catalogue")
CONFIG_DIR = os.path.join(ROOT, "config")
DOCS_DIR = os.path.join(ROOT, "docs")
INPUTS_DIR = os.path.join(ROOT, "inputs")
FIXTURES = os.path.join(TESTS_DIR, "fixtures")
SAMPLE_CATALOGUE = os.path.join(FIXTURES, "sample_catalogue")
SAMPLE_CONFIG = os.path.join(FIXTURES, "sample_config.json")
SAMPLE_INPUTS = os.path.join(FIXTURES, "sample_inputs")
HAND_DIR = os.path.join(FIXTURES, "hand")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import applicability  # noqa: E402
import catalogue  # noqa: E402
import ingest_hissrat  # noqa: E402
import roadmap  # noqa: E402
import score  # noqa: E402
import settings  # noqa: E402
from common import read_csv, read_json  # noqa: E402,F401

_CACHE = {}


def real_catalogue():
    """The real catalogue, loaded once. Tests must not change it (use copy.deepcopy when a change is needed)."""
    if "real" not in _CACHE:
        _CACHE["real"] = catalogue.load_catalogue(CATALOGUE_DIR)
    return _CACHE["real"]


def real_config():
    if "config" not in _CACHE:
        _CACHE["config"] = read_json(os.path.join(CONFIG_DIR, "assessment_config.json"))
    return _CACHE["config"]


def load_hand(name):
    """Read a hand calculated fixture and expand its compact rows into the dicts the code expects."""
    fx = read_json(os.path.join(HAND_DIR, name + ".json"))
    controls = []
    for c in fx["controls"]:
        row = dict(c)
        row.setdefault("title", "Control " + c["control_id"])
        row.setdefault("triggers", "")
        row.setdefault("owner_owned", "property")
        row.setdefault("owner_managed", "vendor")
        row.setdefault("owner_franchised", "franchisee")
        controls.append(row)
    fx["controls"] = controls
    fx["controls_by_id"] = {c["control_id"]: c for c in controls}
    fx["crosswalk_rows"] = [
        {"control_id": r[0], "framework": r[1], "target_id": r[2], "target_title": "t " + r[2], "strength": r[3],
         "source": "fixture source" if r[3] == "D" else "", "target_status": r[4]}
        for r in fx.get("crosswalk", [])]
    obligations = []
    for o in fx.get("obligations", []):
        obligations.append({"obligation_id": o[0], "jurisdiction": o[1], "hotel_trigger": o[2], "status": o[3],
                            "control_ids": o[4], "instrument": "fixture instrument", "provision": "fixture provision"})
    fx["obligation_rows"] = obligations
    universe = {}
    for fw, ids in fx.get("universe", {}).items():
        universe[fw] = [{"id": i, "title": "t " + i} for i in ids]
    fx["universe_map"] = universe
    return fx


def run_hand(fx, prop, answers=None, caps=None, config_override=None):
    """Settings, applicability rows and control scores for one property of a hand fixture."""
    raw = copy.deepcopy(fx["config"])
    if config_override:
        raw.update(config_override)
    cfg = settings.property_settings(raw, prop)
    app = applicability.filter_controls(fx["controls"], cfg)
    ans = fx["answers"][prop] if answers is None else answers
    answers_dict = {cid: {"maturity": m, "evidence_ref": "", "comment": ""} for cid, m in ans.items()}
    rows = score.score_controls(app, fx["controls_by_id"], answers_dict, caps or {}, cfg)
    return cfg, app, rows
