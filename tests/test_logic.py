"""Applicability, maturity caps, coverage weights, roadmap ordering and waves, questionnaire parsing, settings."""
import copy
import unittest

import support
import applicability
import ingest_hissrat
import roadmap
import score
import settings
import template

CAT = support.real_catalogue()
CONTROLS = CAT["controls"]
ALL_TRIGGERS = ["T1", "T2", "T3", "T4", "T5"]


def cfg_for(profile, triggers=(), **extra):
    raw = {"profile": profile, "triggers": list(triggers)}
    raw.update(extra)
    return settings.property_settings(raw, "TEST")


def applicable(profile, triggers=()):
    cfg = cfg_for(profile, triggers)
    return set(applicability.applicable_ids(applicability.filter_controls(CONTROLS, cfg)))


class ApplicabilityRealCatalogue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = {c["control_id"] for c in CONTROLS if c["level"] == "Baseline"}
        cls.enhanced = [c for c in CONTROLS if c["level"] == "Enhanced"]

    def test_profile_s_without_triggers_gets_baseline_only(self):
        self.assertEqual(applicable("S"), self.baseline)
        self.assertEqual(len(self.baseline), 63)

    def test_profiles_m_and_g_get_every_control(self):
        everything = {c["control_id"] for c in CONTROLS}
        self.assertEqual(applicable("M"), everything)
        self.assertEqual(applicable("G"), everything)

    def test_baseline_applies_to_every_profile_and_trigger_set(self):
        for profile in ("S", "M", "G"):
            for trig in ([], ["T1"], ALL_TRIGGERS):
                self.assertTrue(self.baseline <= applicable(profile, trig), (profile, trig))

    def test_each_trigger_makes_its_enhanced_controls_mandatory_for_s(self):
        triggered = [c for c in self.enhanced if c["trigger_list"]]
        self.assertGreater(len(triggered), 0)
        for c in triggered:
            cid = c["control_id"]
            for t in c["trigger_list"]:
                self.assertIn(cid, applicable("S", [t]), "%s should apply to S when %s is active" % (cid, t))
            others = [t for t in ALL_TRIGGERS if t not in c["trigger_list"]]
            self.assertNotIn(cid, applicable("S", others), "%s must not apply to S for unrelated triggers" % cid)
            self.assertNotIn(cid, applicable("S"), cid)

    def test_s_with_all_triggers_adds_exactly_the_triggered_enhanced_controls(self):
        triggered = {c["control_id"] for c in self.enhanced if c["trigger_list"]}
        self.assertEqual(applicable("S", ALL_TRIGGERS), self.baseline | triggered)

    def test_enhanced_without_trigger_never_reaches_s(self):
        plain = {c["control_id"] for c in self.enhanced if not c["trigger_list"]}
        self.assertGreater(len(plain), 0)
        self.assertFalse(plain & applicable("S", ALL_TRIGGERS))

    def test_triggers_do_not_change_m_or_g(self):
        self.assertEqual(applicable("M", ALL_TRIGGERS), applicable("M"))
        self.assertEqual(applicable("G", ["T3"]), applicable("G"))

    def test_applicability_rows_carry_reason_and_active_triggers(self):
        rows = applicability.filter_controls(CONTROLS, cfg_for("S", ["T3"]))
        self.assertEqual(len(rows), len(CONTROLS))
        by = {r["control_id"]: r for r in rows}
        self.assertEqual(by["HISS-H06-01"]["applicable"], "yes")
        self.assertEqual(by["HISS-H06-01"]["active_triggers"], "T3")
        self.assertIn("trigger T3", by["HISS-H06-01"]["reason"])
        self.assertEqual(by["HISS-H09-02"]["applicable"], "no")
        self.assertTrue(all(r["reason"] for r in rows))

    def test_accountable_party_follows_operating_model(self):
        c = CONTROLS[0]
        for model, field in (("owned", "owner_owned"), ("managed", "owner_managed"), ("franchised", "owner_franchised")):
            self.assertEqual(applicability.accountable_party(c, model), c[field])


class ControlAppliesUnit(unittest.TestCase):
    def ctl(self, level, profiles, triggers=""):
        return {"level": level, "profiles": profiles, "triggers": triggers}

    def test_baseline_always_applies(self):
        ok, reason, matched = applicability.control_applies(self.ctl("Baseline", "S;M;G"), "S", set())
        self.assertTrue(ok)
        self.assertEqual(matched, [])

    def test_enhanced_listed_for_profile(self):
        self.assertTrue(applicability.control_applies(self.ctl("Enhanced", "M;G"), "G", set())[0])
        self.assertFalse(applicability.control_applies(self.ctl("Enhanced", "M;G"), "S", set())[0])

    def test_enhanced_trigger_match_lists_all_matched_triggers(self):
        ok, reason, matched = applicability.control_applies(self.ctl("Enhanced", "M;G", "T1;T4"), "S", {"T1", "T4", "T5"})
        self.assertTrue(ok)
        self.assertEqual(matched, ["T1", "T4"])
        self.assertIn("T1 and T4", reason)

    def test_enhanced_trigger_not_active(self):
        ok, reason, matched = applicability.control_applies(self.ctl("Enhanced", "M;G", "T2"), "S", {"T1"})
        self.assertFalse(ok)
        self.assertEqual(matched, [])

    def test_jurisdiction_tag_matching(self):
        m = applicability.jurisdiction_matches
        self.assertTrue(m("AE-DXB", "AE"))
        self.assertTrue(m("AE", "AE-DXB"))
        self.assertTrue(m("US-NY", "US"))
        self.assertTrue(m("in", "IN"))
        self.assertFalse(m("AE-DXB", "AE-AUH"))
        self.assertFalse(m("AEX", "AE"))
        self.assertFalse(m("EU-DE", "UK"))

    def test_obligation_trigger_text_needs_active_trigger(self):
        cfg = cfg_for("M", [], jurisdictions={"EU": "judged"})
        ob = {"jurisdiction": "EU-DE", "hotel_trigger": "T5 guests from a listed jurisdiction"}
        self.assertFalse(applicability.obligation_scope(ob, cfg)[0])
        cfg = cfg_for("M", ["T5"], jurisdictions={"EU": "judged"})
        ok, basis, _ = applicability.obligation_scope(ob, cfg)
        self.assertTrue(ok)
        self.assertEqual(basis, "judged")


class SettingsRules(unittest.TestCase):
    def test_defaults_match_the_documented_assumed_values(self):
        d = settings.DEFAULTS
        self.assertEqual(d["strength_weights"], {"D": 1.0, "P": 0.5, "J": 0.25})
        self.assertEqual(d["finding_caps"], {"Critical": 1, "High": 1, "Medium": 2})
        self.assertEqual(d["level_weights"], {"Baseline": 2.0, "Enhanced": 1.0})
        self.assertEqual(d["effort_weights"], {"S": 1, "M": 2, "L": 3})
        self.assertEqual(d["met_threshold"], 3)
        self.assertEqual(d["target_maturity"], 3)

    def test_shipped_config_matches_the_readme_values(self):
        cfg = settings.property_settings(support.real_config(), "PROP-C")
        self.assertEqual(cfg["strength_weights"], {"D": 1.0, "P": 0.5, "J": 0.25})
        self.assertEqual(cfg["finding_caps"], {"Critical": 1, "High": 1, "Medium": 2})
        self.assertEqual(cfg["tier_weights"], {1: 5.0, 2: 3.0, 3: 2.0, 4: 1.0})
        self.assertEqual((cfg["waves"]["wave1_min_priority"], cfg["waves"]["wave2_min_priority"]), (10, 4))
        self.assertEqual(settings.check_settings(cfg), [])

    def test_property_override_and_normalisation(self):
        raw = {"profile": "M", "triggers": ["t1"], "properties": {"prop-f": {"profile": "s", "triggers": ["t5"]}}}
        cfg = settings.property_settings(raw, "PROP-F")
        self.assertEqual(cfg["profile"], "S")
        self.assertEqual(cfg["triggers"], ["T5"])
        self.assertEqual(settings.property_settings(raw, "OTHER")["triggers"], ["T1"])

    def test_check_settings_reports_problems(self):
        cfg = cfg_for("X", ["T9"])
        problems = settings.check_settings(cfg)
        self.assertTrue(any("profile" in p for p in problems))
        self.assertTrue(any("T9" in p for p in problems))


class CapRule(unittest.TestCase):
    FAMS = {"fam": ["C1", "C2"], "other": ["C3"]}
    RULES = {"Critical": 1, "High": 1, "Medium": 2}

    def caps(self, findings, systems=None):
        systems = systems or [{"system_id": "S1", "property": "P", "tier": 1}]
        for f in findings:
            f.setdefault("plugin_name", "x")
        return ingest_hissrat.derive_caps(findings, systems, self.FAMS, self.RULES)

    def f(self, sev, fam="fam", sid="S1"):
        return {"system_id": sid, "severity": sev, "family": fam}

    def test_critical_caps_at_one(self):
        caps = self.caps([self.f("Critical")])
        self.assertEqual(caps["C1"]["cap"], 1)
        self.assertEqual(caps["C2"]["cap"], 1)

    def test_high_caps_at_one(self):
        self.assertEqual(self.caps([self.f("High")])["C1"]["cap"], 1)

    def test_medium_caps_at_two(self):
        self.assertEqual(self.caps([self.f("Medium")])["C1"]["cap"], 2)

    def test_low_and_info_set_no_cap(self):
        self.assertEqual(self.caps([self.f("Low"), self.f("Info")]), {})

    def test_lowest_cap_wins_when_findings_mix(self):
        caps = self.caps([self.f("Medium"), self.f("High")])
        self.assertEqual(caps["C1"]["cap"], 1)
        self.assertEqual(caps["C1"]["severity"], "High")
        self.assertEqual(caps["C1"]["findings"], 2)

    def test_only_linked_family_controls_are_capped(self):
        caps = self.caps([self.f("Critical", "other")])
        self.assertEqual(sorted(caps), ["C3"])

    def test_out_of_scope_system_and_unmapped_family_are_ignored(self):
        caps = self.caps([self.f("Critical", sid="S9"), self.f("Critical", fam="nonesuch")])
        self.assertEqual(caps, {})

    def test_apply_cap_lowers_but_never_raises(self):
        self.assertEqual(ingest_hissrat.apply_cap(4, 1), 1)
        self.assertEqual(ingest_hissrat.apply_cap(3, 2), 2)
        self.assertEqual(ingest_hissrat.apply_cap(0, 1), 0)
        self.assertEqual(ingest_hissrat.apply_cap(1, 2), 1)
        self.assertEqual(ingest_hissrat.apply_cap(3, None), 3)
        self.assertIsNone(ingest_hissrat.apply_cap(None, 1))

    def test_cap_flows_through_scoring(self):
        cfg = cfg_for("M")
        app = [{"control_id": "C1", "applicable": "yes", "accountable": "property"},
               {"control_id": "C2", "applicable": "yes", "accountable": "property"}]
        controls = {c: {"control_id": c, "domain": "F5", "title": c, "level": "Baseline"} for c in ("C1", "C2")}
        answers = {"C1": {"maturity": 4}, "C2": {"maturity": 1}}
        caps = {"C1": {"cap": 2, "reasons": ["Medium on S1 (fam)"]}, "C2": {"cap": 2, "reasons": []}}
        rows = {r["control_id"]: r for r in score.score_controls(app, controls, answers, caps, cfg)}
        self.assertEqual(rows["C1"]["maturity"], 2)
        self.assertEqual(rows["C1"]["capped"], "yes")
        self.assertEqual(rows["C1"]["met"], "no")
        self.assertEqual(rows["C2"]["maturity"], 1, "a cap never raises a low score")
        self.assertEqual(rows["C2"]["capped"], "no")


def one_control_view(maturity, strength, status="VERIFIED", cfg=None):
    cfg = cfg or cfg_for("M")
    rows = [{"control_id": "C1", "maturity": maturity}]
    xw = [{"control_id": "C1", "framework": "CIS", "target_id": "5", "target_title": "t", "strength": strength,
           "source": "s" if strength == "D" else "", "target_status": status}]
    view = score.standard_view(rows, xw, cfg)
    return view["rows"][0]


class CoverageWeights(unittest.TestCase):
    def test_weights_d_p_j_at_full_maturity(self):
        self.assertEqual(one_control_view(4, "D")["indicative_pct"], 100.0)
        self.assertEqual(one_control_view(4, "P")["indicative_pct"], 50.0)
        self.assertEqual(one_control_view(4, "J")["indicative_pct"], 25.0)

    def test_weights_scale_with_maturity(self):
        self.assertEqual(one_control_view(2, "D")["indicative_pct"], 50.0)
        self.assertEqual(one_control_view(2, "P")["indicative_pct"], 25.0)
        self.assertEqual(one_control_view(2, "J")["indicative_pct"], 12.5)
        self.assertEqual(one_control_view(0, "D")["indicative_pct"], 0.0)

    def test_source_backed_counts_direct_rows_only(self):
        self.assertEqual(one_control_view(4, "D")["source_backed_pct"], 100.0)
        self.assertEqual(one_control_view(4, "P")["source_backed_pct"], 0.0)
        self.assertEqual(one_control_view(4, "J")["source_backed_pct"], 0.0)

    def test_secondary_target_is_indicative_but_not_source_backed(self):
        r = one_control_view(4, "D", status="SECONDARY")
        self.assertEqual(r["indicative_pct"], 100.0)
        self.assertEqual(r["source_backed_pct"], 0.0)

    def test_not_verified_target_is_never_scored(self):
        r = one_control_view(4, "D", status="NOT VERIFIED")
        self.assertEqual(r["indicative_pct"], "")
        self.assertEqual(r["source_backed_pct"], "")
        self.assertIn("NOT VERIFIED", r["state"])

    def test_coverage_is_the_maximum_not_the_sum(self):
        cfg = cfg_for("M")
        rows = [{"control_id": "A", "maturity": 4}, {"control_id": "B", "maturity": 4}, {"control_id": "C", "maturity": 4}]
        xw = [{"control_id": c, "framework": "CIS", "target_id": "5", "target_title": "t", "strength": "P", "source": "",
               "target_status": "VERIFIED"} for c in "ABC"]
        self.assertEqual(score.standard_view(rows, xw, cfg)["rows"][0]["indicative_pct"], 50.0)

    def test_strength_weights_come_from_settings(self):
        cfg = cfg_for("M", strength_weights={"P": 0.4})
        self.assertEqual(cfg["strength_weights"], {"D": 1.0, "P": 0.4, "J": 0.25})
        self.assertEqual(one_control_view(4, "P", cfg=cfg)["indicative_pct"], 40.0)

    def test_clause_roll_up(self):
        self.assertEqual(score.clause_key("PCIDSS", "8.3.1"), "8")
        self.assertEqual(score.clause_key("CSF", "PR.AA-01"), "PR.AA")
        self.assertEqual(score.clause_key("CIS", "5.2"), "5")
        self.assertEqual(score.clause_key("CCM", "IAM-02"), "IAM")
        self.assertEqual(score.clause_key("ISO27001", "A.8.20"), "A.8.20")


def ctl_row(cid, domain, level, maturity, answered="yes"):
    return {"control_id": cid, "domain": domain, "title": cid, "level": level, "maturity": maturity,
            "answered": answered, "accountable": "property"}


class RoadmapRules(unittest.TestCase):
    def build(self, rows, caps=None, **extra):
        cfg = cfg_for("M", **extra)
        by_id = {r["control_id"]: r for r in rows}
        return roadmap.build_roadmap(rows, by_id, caps or {}, cfg), cfg

    def test_priority_formula(self):
        self.assertEqual(roadmap.priority_of(2, 5, 3, 1), 30)
        self.assertAlmostEqual(roadmap.priority_of(1, 2, 2, 3), 4 / 3)

    def test_higher_priority_ranks_first(self):
        rows = [ctl_row("LOW", "F1", "Enhanced", 2), ctl_row("HIGH", "F4", "Baseline", 0)]
        items, _ = self.build(rows, domain_default_tier={"F1": 4, "F4": 1})
        self.assertEqual([i["control_id"] for i in items], ["HIGH", "LOW"])
        self.assertGreater(items[0]["priority"], items[1]["priority"])
        self.assertEqual([i["rank"] for i in items], [1, 2])

    def test_baseline_outranks_enhanced_all_else_equal(self):
        rows = [ctl_row("E", "F1", "Enhanced", 1), ctl_row("B", "F1", "Baseline", 1)]
        items, _ = self.build(rows)
        self.assertEqual(items[0]["control_id"], "B")

    def test_larger_gap_and_smaller_effort_rank_higher(self):
        rows = [ctl_row("BIG", "F1", "Baseline", 0), ctl_row("SMALL", "F1", "Baseline", 2)]
        items, _ = self.build(rows)
        self.assertEqual(items[0]["control_id"], "BIG")
        rows = [ctl_row("EASY", "F1", "Baseline", 1), ctl_row("HARD", "F2", "Baseline", 1)]
        items, _ = self.build(rows, effort_by_control={"EASY": "S", "HARD": "L"})
        self.assertEqual(items[0]["control_id"], "EASY")

    def test_ties_break_by_domain_order_then_control_id(self):
        rows = [ctl_row("B2", "H01", "Baseline", 1), ctl_row("A1", "F4", "Baseline", 1), ctl_row("A0", "F4", "Baseline", 1)]
        items, _ = self.build(rows)
        self.assertEqual([i["control_id"] for i in items], ["A0", "A1", "B2"])

    def test_controls_at_or_above_target_are_left_out(self):
        rows = [ctl_row("OK", "F1", "Baseline", 3), ctl_row("BEST", "F1", "Baseline", 4), ctl_row("GAP", "F1", "Baseline", 2)]
        items, _ = self.build(rows)
        self.assertEqual([i["control_id"] for i in items], ["GAP"])

    def test_wave_cut_offs_are_inclusive(self):
        cfg = cfg_for("M")
        self.assertEqual(roadmap.wave_of("X", 10, cfg), 1)
        self.assertEqual(roadmap.wave_of("X", 9.99, cfg), 2)
        self.assertEqual(roadmap.wave_of("X", 4, cfg), 2)
        self.assertEqual(roadmap.wave_of("X", 3.99, cfg), 3)
        self.assertEqual(roadmap.wave_of("X", 0.5, cfg), 3)

    def test_wave_override_wins(self):
        cfg = cfg_for("M", wave_overrides={"X": 1, "Y": 3})
        self.assertEqual(roadmap.wave_of("X", 0.1, cfg), 1)
        self.assertEqual(roadmap.wave_of("Y", 99, cfg), 3)
        self.assertEqual(roadmap.wave_of("Z", 99, cfg), 1)

    def test_wave_numbers_never_decrease_down_the_ranking(self):
        rows = [ctl_row("C%02d" % i, d, lv, m) for i, (d, lv, m) in enumerate(
            [("F4", "Baseline", 0), ("F1", "Enhanced", 2), ("H03", "Baseline", 2), ("H05", "Enhanced", 0),
             ("F6", "Baseline", 1), ("H07", "Baseline", 0)])]
        items, cfg = self.build(rows, domain_default_tier=support.real_config()["domain_default_tier"],
                                effort_by_domain=support.real_config()["effort_by_domain"])
        waves = [i["wave"] for i in items]
        self.assertEqual(waves, sorted(waves))
        self.assertGreater(len(set(waves)), 1, "this mix should span more than one wave")

    def test_tier_uses_most_critical_system_else_domain_default(self):
        rows = [ctl_row("A", "F4", "Baseline", 0), ctl_row("B", "F4", "Baseline", 0)]
        caps = {"A": {"tiers": [3, 2], "systems": ["S1", "S2"], "reasons": ["r"]}}
        items, cfg = self.build(rows, caps, domain_default_tier={"F4": 4})
        by = {i["control_id"]: i for i in items}
        self.assertEqual(by["A"]["tier"], 2)
        self.assertEqual(by["A"]["tier_weight"], 3.0)
        self.assertEqual(by["A"]["tier_source"], "HISS-RAT affected systems")
        self.assertEqual(by["B"]["tier"], 4)
        self.assertEqual(by["B"]["tier_source"], "domain default (assumed)")

    def test_effort_precedence_control_then_domain_then_default(self):
        cfg = cfg_for("M", effort_by_control={"X": "L"}, effort_by_domain={"F1": "S"})
        self.assertEqual(roadmap.effort_of("X", "F1", cfg), "L")
        self.assertEqual(roadmap.effort_of("Y", "F1", cfg), "S")
        self.assertEqual(roadmap.effort_of("Y", "F2", cfg), "M")

    def test_unanswered_control_is_marked_not_assessed(self):
        items, _ = self.build([ctl_row("U", "F1", "Baseline", 0, answered="no")])
        self.assertIn("not assessed", items[0]["drivers"])

    def test_domain_priority_sums_exact_priorities(self):
        rows = [ctl_row("A", "F1", "Baseline", 0), ctl_row("B", "F1", "Baseline", 1), ctl_row("C", "F2", "Baseline", 2)]
        items, _ = self.build(rows)
        dp = roadmap.domain_priority(items)
        self.assertAlmostEqual(dp["F1"], sum(i["_priority_exact"] for i in items if i["domain"] == "F1"))
        self.assertEqual(set(dp), {"F1", "F2"})


class QuestionnaireParsing(unittest.TestCase):
    def setUp(self):
        self.by_id = {c: {"control_id": c} for c in ("C1", "C2", "C3", "C4")}
        self.applic = ["C1", "C2", "C3"]

    def parse(self, rows):
        return template.parse_assessment(rows, self.by_id, self.applic)

    def test_blank_template_lists_applicable_controls_only(self):
        app = [{"control_id": "C1", "applicable": "yes"}, {"control_id": "C2", "applicable": "no"}]
        rows = template.template_rows(app)
        self.assertEqual([r["control_id"] for r in rows], ["C1"])
        self.assertEqual(rows[0]["maturity"], "")

    def test_valid_answers_and_blank(self):
        answers, problems = self.parse([
            {"control_id": "C1", "maturity": "3", "evidence_ref": "doc"},
            {"control_id": "C2", "maturity": ""},
            {"control_id": "C3", "maturity": "4.0", "evidence_ref": "doc"}])
        self.assertEqual(answers["C1"]["maturity"], 3)
        self.assertIsNone(answers["C2"]["maturity"])
        self.assertEqual(answers["C3"]["maturity"], 4)
        self.assertEqual(problems, [])

    def test_out_of_range_and_non_integer_values_are_treated_as_blank(self):
        answers, problems = self.parse([
            {"control_id": "C1", "maturity": "5"}, {"control_id": "C2", "maturity": "2.5"},
            {"control_id": "C3", "maturity": "high"}])
        for cid in self.applic:
            self.assertIsNone(answers[cid]["maturity"], cid)
        self.assertEqual(len(problems), 3)

    def test_unknown_inapplicable_and_duplicate_rows_are_reported(self):
        answers, problems = self.parse([
            {"control_id": "NOPE", "maturity": "2"}, {"control_id": "C4", "maturity": "2"},
            {"control_id": "C1", "maturity": "1"}, {"control_id": "C1", "maturity": "2"}])
        text = " | ".join(problems)
        self.assertIn("not in the catalogue", text)
        self.assertIn("does not apply", text)
        self.assertIn("appears twice", text)
        self.assertEqual(answers["C1"]["maturity"], 2, "the last row is used")
        self.assertNotIn("C4", answers)
        self.assertIn("2 applicable controls have no row", text)

    def test_rating_of_three_or_more_without_evidence_is_flagged(self):
        _, problems = self.parse([{"control_id": "C1", "maturity": "3", "evidence_ref": ""},
                                  {"control_id": "C2", "maturity": "2", "evidence_ref": ""},
                                  {"control_id": "C3", "maturity": "0"}])
        flagged = [p for p in problems if "no evidence reference" in p]
        self.assertEqual(len(flagged), 1)
        self.assertIn("C1", flagged[0])


if __name__ == "__main__":
    unittest.main()
