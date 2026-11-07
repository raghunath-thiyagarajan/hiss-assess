"""Tests for the follow up changes: role aware caps (A25), capped_by_scan, wave cut off sensitivity, the sub level
clause view, the hand classification file for the ISO only comparison and the unused trigger check.

All data is small and made up inside the tests. Nothing here reads or writes inputs/ or outputs/.
"""
import os
import tempfile
import unittest

import support
import catalogue as cat_mod
import gap
import ingest_hissrat
import pipeline
import roadmap
import score
import settings
import template
import applicability
from common import DOMAIN_ORDER, read_csv

ROLES = ingest_hissrat.load_system_roles()
FAMS = {"fam": ["C1", "C2", "C3"]}
RULES = {"Critical": 1, "High": 1, "Medium": 2}
DOMAIN_OF = {"C1": "F5", "C2": "H07", "C3": "H03"}


def system(sid, role_key, tier=1):
    return {"system_id": sid, "property": "P", "tier": tier, "role_key": role_key, "role": ""}


def finding(sid, sev, fam="fam"):
    return {"system_id": sid, "severity": sev, "family": fam, "plugin_name": "plugin " + sev}


def cfg_for(profile="M", **extra):
    raw = {"profile": profile, "triggers": []}
    raw.update(extra)
    return settings.property_settings(raw, "TEST")


class RoleAwareCaps(unittest.TestCase):
    def caps(self, findings, systems, roles=ROLES):
        return ingest_hissrat.derive_caps_ex(findings, systems, FAMS, RULES, DOMAIN_OF, roles)

    def test_finding_on_one_role_does_not_cap_unrelated_domains(self):
        caps, notes = self.caps([finding("S1", "Critical")], [system("S1", "ad")])
        self.assertIn("C2", caps, "the domain controller role covers H07")
        self.assertNotIn("C3", caps, "H03 is a guest network domain and is not a domain controller concern")
        self.assertEqual(notes["skipped"], 1)

    def test_foundation_domains_are_capped_for_every_role(self):
        for key in ("ad", "pms", "inroom", "cctv", "hr"):
            caps, _ = self.caps([finding("S1", "High")], [system("S1", key)])
            self.assertEqual(caps["C1"]["cap"], 1, "F5 control is capped for role key %s" % key)

    def test_each_system_is_judged_by_its_own_role(self):
        fs = [finding("S1", "Critical"), finding("S2", "Medium")]
        caps, _ = self.caps(fs, [system("S1", "ad"), system("S2", "interface")])
        self.assertEqual(caps["C3"]["systems"], ["S2"], "only the interface server reaches H03")
        self.assertEqual(caps["C3"]["cap"], 2)
        self.assertEqual(caps["C2"]["systems"], ["S1", "S2"])
        self.assertEqual(caps["C2"]["cap"], 1)

    def test_unknown_role_falls_back_and_is_reported(self):
        caps, notes = self.caps([finding("S1", "Critical")], [system("S1", "mystery_box")])
        self.assertEqual(sorted(caps), ["C1", "C2", "C3"], "earlier behaviour: every linked control is capped")
        self.assertEqual(notes["unknown_roles"], ["mystery_box"])
        self.assertEqual(notes["skipped"], 0)

    def test_blank_role_counts_as_unknown(self):
        _, notes = self.caps([finding("S1", "High")], [system("S1", "")])
        self.assertEqual(notes["unknown_roles"], ["blank role"])

    def test_role_rule_is_off_without_a_domain_map_or_role_file(self):
        fs, sy = [finding("S1", "Critical")], [system("S1", "ad")]
        caps, notes = ingest_hissrat.derive_caps_ex(fs, sy, FAMS, RULES)
        self.assertEqual(sorted(caps), ["C1", "C2", "C3"])
        self.assertFalse(notes["role_rule"])
        caps2, notes2 = ingest_hissrat.derive_caps_ex(fs, sy, FAMS, RULES, DOMAIN_OF, None)
        self.assertFalse(notes2["role_rule"])
        self.assertEqual(sorted(caps2), ["C1", "C2", "C3"])

    def test_derive_caps_wrapper_returns_only_the_caps(self):
        fs, sy = [finding("S1", "Critical")], [system("S1", "ad")]
        wrapped = ingest_hissrat.derive_caps(fs, sy, FAMS, RULES, DOMAIN_OF, ROLES)
        self.assertEqual(wrapped, self.caps(fs, sy)[0])

    def test_allowed_domains_by_key_by_label_and_unknown(self):
        by_key = ingest_hissrat.allowed_domains({"role_key": "ad"}, ROLES)
        by_label = ingest_hissrat.allowed_domains({"role_key": "", "role": "AD (domain controller)"}, ROLES)
        self.assertEqual(by_key, by_label)
        self.assertIn("H07", by_key)
        self.assertNotIn("H03", by_key)
        self.assertTrue({"F1", "F2", "F3", "F4", "F5", "F6"} <= by_key)
        self.assertIsNone(ingest_hissrat.allowed_domains({"role_key": "nothing", "role": "Nothing"}, ROLES))

    def test_role_file_is_consistent(self):
        self.assertEqual(ROLES["foundation_domains"], ["F1", "F2", "F3", "F4", "F5", "F6"])
        for cls, spec in ROLES["role_classes"].items():
            self.assertTrue(spec["domains"], cls)
            self.assertTrue(set(spec["domains"]) <= set(DOMAIN_ORDER), cls)
        for table in ("role_keys", "role_labels"):
            for name, cls in ROLES[table].items():
                self.assertIn(cls, ROLES["role_classes"], "%s %s points at a class that does not exist" % (table, name))


class CappedByScan(unittest.TestCase):
    def rows(self, self_maturity, cap):
        cfg = cfg_for()
        app = [{"control_id": "C1", "applicable": "yes", "accountable": "property"}]
        controls = {"C1": {"control_id": "C1", "domain": "F5", "title": "t", "level": "Baseline"}}
        answers = {"C1": {"maturity": self_maturity}} if self_maturity is not None else {}
        caps = {"C1": {"cap": cap, "reasons": ["High on S1 (fam)"]}} if cap is not None else {}
        return score.score_controls(app, controls, answers, caps, cfg)[0]

    def test_yes_only_when_the_cap_lowered_the_maturity(self):
        r = self.rows(4, 1)
        self.assertEqual((r["capped_by_scan"], r["maturity"], r["self_maturity"]), ("yes", 1, 4))

    def test_no_when_a_cap_exists_but_did_not_bite(self):
        for selfm in (1, 2, 0):
            r = self.rows(selfm, 2)
            self.assertEqual(r["capped_by_scan"], "no", "self %s under cap 2" % selfm)
            self.assertEqual(r["cap"], 2, "the cap is still shown")
            self.assertEqual(r["maturity"], selfm)

    def test_unanswered_control_is_never_capped_by_scan(self):
        r = self.rows(None, 1)
        self.assertEqual((r["answered"], r["capped_by_scan"], r["maturity"]), ("no", "no", 0))

    def test_legacy_capped_column_always_matches(self):
        for selfm, cap in ((4, 1), (1, 2), (3, None), (None, 1), (2, 2)):
            r = self.rows(selfm, cap)
            self.assertEqual(r["capped"], r["capped_by_scan"])

    def test_domain_and_overall_counts_use_the_same_meaning(self):
        base = {"title": "t", "level": "Baseline", "accountable": "property", "answered": "yes", "met": "no"}
        rows = [dict(base, control_id="A", domain="F5", maturity=1, capped_by_scan="yes", capped="yes"),
                dict(base, control_id="B", domain="F5", maturity=2, capped_by_scan="no", capped="no"),
                dict(base, control_id="C", domain="H07", maturity=1, capped_by_scan="yes", capped="yes")]
        doms = score.domain_scores(rows)
        self.assertEqual({d["domain"]: d["capped_by_scan"] for d in doms}, {"F5": 1, "H07": 1})
        self.assertTrue(all(d["capped"] == d["capped_by_scan"] for d in doms))
        self.assertEqual(score.property_score(rows, doms)["capped_by_scan"], 2)
        self.assertEqual(score.property_score([], [])["capped_by_scan"], 0)


class WaveCutoffSensitivity(unittest.TestCase):
    def items(self, priorities, cfg):
        out = []
        for n, p in enumerate(priorities, 1):
            cid = "X%d" % n
            out.append({"control_id": cid, "domain": "F5", "title": "t", "level": "Baseline", "priority": round(p, 2),
                        "_priority_exact": p, "wave": roadmap.wave_of(cid, p, cfg)})
        return out

    def test_only_items_near_a_cut_off_are_listed(self):
        cfg = cfg_for()
        res = roadmap.wave_cutoff_sensitivity(self.items([13, 11, 9, 4.5, 3.5, 2], cfg), cfg)
        moved = {r["control_id"]: r for r in res["rows"]}
        self.assertEqual(sorted(moved), ["X2", "X3", "X4", "X5"])
        self.assertEqual((moved["X2"]["wave_base"], moved["X2"]["wave_cutoffs_plus20"]), (1, 2))
        self.assertEqual((moved["X3"]["wave_base"], moved["X3"]["wave_cutoffs_minus20"]), (2, 1))
        self.assertEqual((moved["X4"]["wave_base"], moved["X4"]["wave_cutoffs_plus20"]), (2, 3))
        self.assertEqual((moved["X5"]["wave_base"], moved["X5"]["wave_cutoffs_minus20"]), (3, 2))

    def test_change_text_says_which_way_the_item_moves(self):
        cfg = cfg_for()
        res = roadmap.wave_cutoff_sensitivity(self.items([11, 9], cfg), cfg)
        text = {r["control_id"]: r["changes"] for r in res["rows"]}
        self.assertEqual(text["X1"], "moves later when cut offs rise")
        self.assertEqual(text["X2"], "moves earlier when cut offs fall")

    def test_item_can_move_both_ways_with_wider_factors(self):
        cfg = cfg_for()
        res = roadmap.wave_cutoff_sensitivity(self.items([6], cfg), cfg, factors=(0.5, 2.0))
        self.assertEqual(len(res["rows"]), 1)
        self.assertEqual(res["rows"][0]["changes"], "moves earlier when cut offs fall and later when they rise")

    def test_summary_has_three_scenarios_that_each_cover_every_item(self):
        cfg = cfg_for()
        its = self.items([13, 11, 9, 4.5, 3.5, 2], cfg)
        res = roadmap.wave_cutoff_sensitivity(its, cfg)
        self.assertEqual([s["scenario"] for s in res["summary"]], ["base", "cut offs x0.8", "cut offs x1.2"])
        for s in res["summary"]:
            self.assertEqual(s["wave1"] + s["wave2"] + s["wave3"], len(its))
        self.assertEqual(res["summary"][0]["wave1"], 2)
        self.assertGreaterEqual(res["summary"][1]["wave1"], res["summary"][0]["wave1"])
        self.assertLessEqual(res["summary"][2]["wave1"], res["summary"][0]["wave1"])

    def test_cutoffs_come_from_the_settings_and_move_by_twenty_percent(self):
        cfg = cfg_for()
        res = roadmap.wave_cutoff_sensitivity(self.items([5], cfg), cfg)
        self.assertEqual(res["cutoffs"], {"wave1": 10, "wave2": 4, "minus20": [8.0, 3.2], "plus20": [12.0, 4.8]})
        cfg2 = cfg_for(waves=dict(cfg["waves"], wave1_min_priority=20, wave2_min_priority=5))
        res2 = roadmap.wave_cutoff_sensitivity(self.items([5], cfg2), cfg2)
        self.assertEqual((res2["cutoffs"]["wave1"], res2["cutoffs"]["wave2"]), (20, 5))
        self.assertEqual(res2["cutoffs"]["plus20"], [24.0, 6.0])

    def test_manual_wave_override_stays_put(self):
        cfg = cfg_for(wave_overrides={"X1": 3})
        res = roadmap.wave_cutoff_sensitivity(self.items([11], cfg), cfg)
        self.assertEqual(res["rows"], [])

    def test_nothing_listed_when_no_item_is_near_a_cut_off(self):
        cfg = cfg_for()
        res = roadmap.wave_cutoff_sensitivity(self.items([30, 1], cfg), cfg)
        self.assertEqual(res["rows"], [])


class SubLevelView(unittest.TestCase):
    CFG = cfg_for()

    def xw(self, cid, fw, tid, strength, status="VERIFIED"):
        return {"control_id": cid, "framework": fw, "target_id": tid, "target_title": "t " + tid,
                "strength": strength, "source": "", "target_status": status}

    def view(self, crosswalk, universe):
        rows = [{"control_id": "C1", "maturity": 4}, {"control_id": "C2", "maturity": 4}]
        res = score.standard_view(rows, crosswalk, self.CFG, universe)
        return {f["framework"]: f for f in res["frameworks"]}, res

    def test_cis_safeguards_roll_up_to_the_control_and_keep_a_sub_level_figure(self):
        cw = [self.xw("C1", "CIS", "4.1", "D"), self.xw("C2", "CIS", "4.2", "J")]
        fw, res = self.view(cw, {"CIS": [{"id": "4", "title": "a"}, {"id": "5", "title": "b"}]})
        cis = fw["CIS"]
        self.assertEqual((cis["clauses_total"], cis["clauses_reached"]), (2, 1))
        self.assertEqual(cis["source_backed_pct_reached"], 100.0, "control 4 is reached through a direct row")
        self.assertEqual(cis["sub_level_clauses"], 2)
        self.assertEqual(cis["sub_level_source_backed_pct"], 50.0, "one safeguard is direct and one is judgement only")
        self.assertEqual(cis["sub_level_indicative_pct"], 62.5)
        self.assertEqual(res["unknown_targets"], [])

    def test_pci_sub_requirements_roll_up_to_the_principal_requirement(self):
        cw = [self.xw("C1", "PCIDSS", "1.2.3", "D"), self.xw("C2", "PCIDSS", "1.3", "P")]
        fw, _ = self.view(cw, {"PCIDSS": [{"id": "1", "title": "a"}, {"id": "2", "title": "b"}]})
        pci = fw["PCIDSS"]
        self.assertEqual(pci["clauses_reached"], 1)
        self.assertEqual(pci["sub_level_clauses"], 2)
        self.assertEqual(pci["sub_level_source_backed_pct"], 50.0)
        self.assertEqual(pci["sub_level_indicative_pct"], 75.0, "a partial row is worth half of a direct row")
        self.assertEqual(pci["source_backed_pct_universe"], 50.0, "one of two principal requirements is covered")

    def test_targets_given_at_clause_level_add_nothing_to_the_sub_level_view(self):
        cw = [self.xw("C1", "CSF", "PR.AA", "D"), self.xw("C1", "CIS", "5", "D")]
        fw, _ = self.view(cw, {"CSF": [{"id": "PR.AA", "title": "a"}], "CIS": [{"id": "5", "title": "b"}]})
        for name in ("CSF", "CIS"):
            self.assertEqual(fw[name]["sub_level_clauses"], 0)
            self.assertIsNone(fw[name]["sub_level_source_backed_pct"])

    def test_not_verified_sub_targets_are_left_out(self):
        cw = [self.xw("C1", "PCIDSS", "1.2.3", "D"), self.xw("C2", "PCIDSS", "2.1", "D", "NOT VERIFIED")]
        fw, _ = self.view(cw, {"PCIDSS": [{"id": "1", "title": "a"}, {"id": "2", "title": "b"}]})
        pci = fw["PCIDSS"]
        self.assertEqual(pci["sub_level_clauses"], 1)
        self.assertIn("2", pci["unreached"], "a clause with only NOT VERIFIED targets counts as not reached")

    def test_sub_level_figures_are_in_the_results_for_the_real_catalogue(self):
        cfg = settings.property_settings(support.real_config(), "PROP-A")
        app = applicability.filter_controls(support.real_catalogue()["controls"], cfg)
        rows = [{"control_id": a["control_id"], "maturity": 2} for a in app if a["applicable"] == "yes"]
        res = score.standard_view(rows, support.real_catalogue()["crosswalk"], cfg,
                                  cat_mod.load_clause_universe(support.real_catalogue()))
        fw = {f["framework"]: f for f in res["frameworks"]}
        for name in ("CIS", "PCIDSS"):
            self.assertGreater(fw[name]["sub_level_clauses"], 0, name)
            self.assertIsNotNone(fw[name]["sub_level_indicative_pct"], name)


class ManualIsoOnlyFile(unittest.TestCase):
    KNOWN = {"R1", "R2", "R3"}

    def test_valid_rows_are_read_and_tidied(self):
        rows = [{"req_id": " R1 ", "class": " Specific ", "reason": " needs a hotel rule "},
                {"req_id": "R2", "class": "ABSENT", "reason": ""}]
        manual, problems = gap.parse_iso_manual(rows, self.KNOWN)
        self.assertEqual(problems, [])
        self.assertEqual(manual["R1"], {"class": "specific", "reason": "needs a hotel rule"})
        self.assertEqual(manual["R2"]["class"], "absent")

    def test_unknown_requirement_and_bad_class_are_ignored_with_a_message(self):
        rows = [{"req_id": "R9", "class": "specific"}, {"req_id": "R2", "class": "partly"}, {"req_id": "R3", "class": "generic"}]
        manual, problems = gap.parse_iso_manual(rows, self.KNOWN)
        self.assertEqual(sorted(manual), ["R3"])
        self.assertEqual(len(problems), 2)
        self.assertIn("row 2", problems[0])
        self.assertIn("R9", problems[0])
        self.assertIn("row 3", problems[1])
        self.assertIn("partly", problems[1])

    def test_blank_requirement_rows_are_skipped_without_a_message(self):
        manual, problems = gap.parse_iso_manual([{"req_id": "", "class": "specific"}, {}], self.KNOWN)
        self.assertEqual((manual, problems), ({}, []))

    def test_reads_a_small_csv_fixture_from_a_temporary_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "iso_only_manual.csv")
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write("req_id,class,reason\nR1,specific,Hotel specific duty\nR2,generic,Plain access control\n")
            manual, problems = gap.parse_iso_manual(read_csv(path), self.KNOWN)
        self.assertEqual(problems, [])
        self.assertEqual({k: v["class"] for k, v in manual.items()}, {"R1": "specific", "R2": "generic"})

    def comparison(self, manual):
        cat = {"control_by_id": {"C1": {}},
               "crosswalk": [{"control_id": "C1", "framework": "ISO27001", "target_id": "A.5.1", "strength": "D",
                              "target_status": "VERIFIED"}],
               "requirements": [{"req_id": "R1", "text": "one", "c1_ref": "", "control_list": ["C1"]},
                                {"req_id": "R2", "text": "two", "c1_ref": "", "control_list": []}]}
        control_rows = [{"control_id": "C1", "met": "no", "title": "t", "maturity": 1}]
        return gap.iso_only_comparison(cat, control_rows, {}, manual)

    def test_manual_class_is_reported_next_to_the_automatic_one(self):
        res = self.comparison({"R1": {"class": "specific", "reason": "hand judgement"}})
        by = {r["req_id"]: r for r in res["rows"]}
        self.assertEqual(by["R1"]["iso_class"], "generic", "the automatic rule is unchanged")
        self.assertEqual(by["R1"]["iso_class_manual"], "specific")
        self.assertEqual(by["R1"]["manual_reason"], "hand judgement")
        self.assertEqual(by["R2"]["iso_class_manual"], "")
        s = res["summary"]
        self.assertTrue(s["manual_file_present"])
        self.assertEqual(s["iso_only_manual"], {"specific": 1, "generic": 0, "absent": 0, "unclassified": 1})
        self.assertEqual(s["matrix_manual_by_hiss"]["specific"]["specific"], 1)

    def test_without_a_manual_file_everything_is_unclassified(self):
        res = self.comparison(None)
        s = res["summary"]
        self.assertFalse(s["manual_file_present"])
        self.assertEqual(s["iso_only_manual"]["unclassified"], 2)
        self.assertEqual(s["iso_only"]["generic"], 1)
        self.assertEqual(s["iso_only"]["absent"], 1)


class UnusedTriggerCheck(unittest.TestCase):
    def test_real_catalogue_reports_t1_as_a_warning_and_not_an_error(self):
        res = cat_mod.validate_catalogue(support.real_catalogue(), full=True)
        hits = [w for w in res["warnings"] if "trigger T1 " in w]
        self.assertEqual(len(hits), 1, res["warnings"])
        self.assertIn("used by no control", hits[0])
        self.assertEqual([e for e in res["errors"] if "trigger" in e.lower()], [])
        self.assertEqual(res["errors"], [])

    def test_only_unused_triggers_are_reported(self):
        res = cat_mod.validate_catalogue(support.real_catalogue(), full=True)
        used = {t for c in support.real_catalogue()["controls"] for t in c["trigger_list"]}
        flagged = {t for t in cat_mod.TRIGGERS if any("trigger %s " % t in w for w in res["warnings"])}
        self.assertEqual(flagged, set(cat_mod.TRIGGERS) - used)
        self.assertEqual(flagged, {"T1"})

    def test_sample_catalogue_uses_t1_and_reports_t5(self):
        res = cat_mod.validate_catalogue(cat_mod.load_catalogue(support.SAMPLE_CATALOGUE), full=True)
        self.assertFalse([w for w in res["warnings"] if "trigger T1 " in w])
        self.assertTrue([w for w in res["warnings"] if "trigger T5 " in w])


class PipelineWithRoles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = cat_mod.load_catalogue(support.SAMPLE_CATALOGUE)
        cls.cfg = settings.property_settings(support.read_json(support.SAMPLE_CONFIG), "SAMPLEHOTEL")
        app = applicability.filter_controls(cls.cat["controls"], cls.cfg)
        cls.answers, _ = template.read_assessment(os.path.join(support.SAMPLE_INPUTS, "assessment_SAMPLEHOTEL.csv"),
                                                  cls.cat["control_by_id"], applicability.applicable_ids(app))
        cls.hissrat = ingest_hissrat.load_hissrat(os.path.join(support.SAMPLE_INPUTS, "hissrat"),
                                                  cls.cfg["hissrat"]["role_tier"])
        cls.universe = cat_mod.load_clause_universe(cls.cat)

    def run_with(self, cfg=None, roles=None):
        return pipeline.run_property(self.cat, cfg or self.cfg, self.answers, hissrat=self.hissrat,
                                     universe=self.universe, system_roles=roles)

    def test_one_capped_by_scan_count_is_used_everywhere(self):
        res = self.run_with()
        n = sum(1 for r in res["controls"] if r["capped_by_scan"] == "yes")
        self.assertGreater(n, 0)
        self.assertEqual(res["overall"]["capped_by_scan"], n)
        self.assertEqual(res["hissrat"]["controls_capped"], n)
        self.assertEqual(sum(d["capped_by_scan"] for d in res["domains"]), n)
        self.assertLessEqual(n, res["hissrat"]["controls_with_cap"])

    def test_role_rule_can_be_switched_off_in_the_settings(self):
        import copy
        cfg = copy.deepcopy(self.cfg)
        cfg["hissrat"]["role_aware"] = False
        res = self.run_with(cfg)
        self.assertFalse(res["hissrat"]["role_rule"]["enabled"])
        self.assertEqual(res["hissrat"]["role_rule"]["cap_applications_skipped"], 0)

    def test_role_rule_removes_caps_a_role_has_no_domain_for(self):
        roles = {"foundation_domains": [], "role_classes": {"none": {"domains": ["F1"]}}, "role_labels": {},
                 "role_keys": {k: "none" for k in ("sql", "ad", "frontdesk", "desktop")}}
        res = self.run_with(roles=roles)
        base = self.run_with()
        self.assertTrue(res["hissrat"]["role_rule"]["enabled"])
        self.assertGreater(res["hissrat"]["role_rule"]["cap_applications_skipped"], 0)
        self.assertLess(res["hissrat"]["controls_with_cap"], base["hissrat"]["controls_with_cap"])
        self.assertLessEqual(res["overall"]["capped_by_scan"], base["overall"]["capped_by_scan"])

    def test_unknown_roles_fall_back_and_add_a_warning_to_the_results(self):
        roles = {"foundation_domains": [], "role_classes": {"none": {"domains": []}}, "role_labels": {}, "role_keys": {}}
        res = self.run_with(roles=roles)
        self.assertEqual(sorted(res["hissrat"]["role_rule"]["unknown_roles"]), ["ad", "frontdesk", "sql"], "only systems with a capping finding are checked")
        self.assertTrue(any("not listed in system_roles" in p for p in res["input"]["problems"]))
        self.assertEqual(res["hissrat"]["role_rule"]["cap_applications_skipped"], 0)
        self.assertEqual(res["hissrat"]["controls_with_cap"], self.run_with()["hissrat"]["controls_with_cap"])

    def test_results_carry_the_wave_sensitivity_table(self):
        res = self.run_with()
        ws = res["roadmap"]["wave_sensitivity"]
        total = len(res["roadmap"]["items"])
        self.assertEqual([s["scenario"] for s in ws["summary"]], ["base", "cut offs x0.8", "cut offs x1.2"])
        for s in ws["summary"]:
            self.assertEqual(s["wave1"] + s["wave2"] + s["wave3"], total)
        self.assertEqual({w["wave"]: w["items"] for w in res["roadmap"]["waves"]},
                         {1: ws["summary"][0]["wave1"], 2: ws["summary"][0]["wave2"], 3: ws["summary"][0]["wave3"]})


if __name__ == "__main__":
    unittest.main()
