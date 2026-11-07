"""Three hand calculated fixtures (tests/fixtures/hand/hand1.json to hand3.json).

The expected numbers were worked out on paper before the code was run. The working is repeated here so a reader
can follow it. Coverage rule: max over mapped applicable controls of weight(strength) x maturity / 4, with
D 1.0, P 0.5 and J 0.25. Source backed uses D rows only. Percentages are rounded to one decimal.

----------------------------------------------------------------------------------------------------------
FIXTURE 1 (hand1.json): profile M, no triggers, no caps. Five controls, all applicable (C4 is Enhanced M;G).
  Maturity: C1 4, C2 2, C3 3, C4 1, C5 blank which counts as 0.
  Met (3 or more): C1 yes, C2 no, C3 yes, C4 no, C5 no.
  Domain F4 (C1, C2): mean (4 + 2) / 2 = 3.0, percent 3.0 / 4 = 75.0, met 1 of 2 = 50.0.
  Domain H02 (C3, C4): mean (3 + 1) / 2 = 2.0, percent 50.0, met 1 of 2 = 50.0.
  Domain H07 (C5): mean 0.0, percent 0.0, met 0 of 1 = 0.0.
  Property: mean (4 + 2 + 3 + 1 + 0) / 5 = 2.0, percent 50.0, met 2 of 5 = 40.0, answered 4 of 5 = 80.0,
            mean of the domain percentages (75.0 + 50.0 + 0.0) / 3 = 41.67 which rounds to 41.7.
  Standard coverage:
    ISO A.5.16: C1 D 1.0 x 4/4 = 1.00, C2 P 0.5 x 2/4 = 0.25. Indicative 100.0. Source backed (C1 only) 100.0.
    ISO A.8.22: C3 D 1.0 x 3/4 = 0.75, C4 J 0.25 x 1/4 = 0.0625. Indicative 75.0, source backed 75.0.
    PCI 1:      C4 D 1.0 x 1/4 = 0.25. Indicative 25.0, source backed 25.0.
    CSF PR.AA:  C1 D 1.00, C2 P 0.25, C5 J 0.25 x 0/4 = 0. Indicative 100.0, source backed 100.0.
    CIS 5:      C2 P 0.5 x 2/4 = 0.25, C4 J 0.25 x 1/4 = 0.0625. Indicative 25.0, source backed 0.0 (no D row).
    ISO framework summary without a clause universe: two clauses reached, mean (1.00 + 0.75) / 2 = 0.875 = 87.5.
  Jurisdiction (IN):
    OBL-IN-1 VERIFIED, C1 and C2: mean 3.0, 75.0 percent, one met of two so partial.
    OBL-IN-2 VERIFIED, C4 and C5: mean (1 + 0) / 2 = 0.5, 12.5 percent, none met so not ready.
    OBL-IN-3 SECONDARY: tracking, never scored.
    OBL-IN-4 VERIFIED, C3: 3.0, 75.0 percent, ready.
    IN roll up: three scored, ready 1, partial 1, not ready 1, tracking 1, mean (75.0 + 12.5 + 75.0) / 3 = 54.17 -> 54.2.

----------------------------------------------------------------------------------------------------------
FIXTURE 2 (hand2.json): profile S with trigger T4, HISS-RAT caps, roadmap.
  Applicable: D1, D2, D3, D6 (Baseline), D4 (Enhanced, not listed for S but trigger T4 is active). D5 needs T3 so it is out.
  Scope: properties ["P"] by default. S1 (tier 1) and S2 (tier 3) belong to P. S3 belongs to Q and is ignored.
  Findings: Critical famA on S1, Medium famA on S2, Medium famB on S2, High famC on S2, Low famB on S1 (no cap), Critical famB on S3 (out of scope).
  Caps: D1 and D2 get min(1, 2) = 1 with systems S1 and S2, so tiers [1, 3]. D3 gets 2 (tier [3]). D4 gets 1 (tier [3]).
  Effective maturity: D1 min(4, 1) = 1, D2 min(3, 1) = 1, D3 min(2, 2) = 2 (not lowered, so capped = no), D4 min(4, 1) = 1, D6 4.
  Domain F5 (D1, D2): mean 1.0, 25.0 percent, met 0, two capped.
  Domain H01 (D3, D6): mean (2 + 4) / 2 = 3.0, 75.0 percent, met 1 of 2 = 50.0, none capped.
  Domain H09 (D4): mean 1.0, 25.0 percent, one capped.
  Property: mean (1 + 1 + 2 + 1 + 4) / 5 = 1.8, 45.0 percent, met 1 of 5 = 20.0, domain percent mean (25 + 75 + 25) / 3 = 41.7.
  Roadmap (target 3, level weights Baseline 2 and Enhanced 1, tier weights 1:5 2:3 3:2 4:1, effort S 1, M 2, L 3):
    D1 gap 2, best tier 1 (weight 5), effort S: 2 x 5 x 2 / 1 = 20.0 -> wave 1.
    D2 gap 2, tier 1 (5), effort M by default: 2 x 5 x 2 / 2 = 10.0 -> wave 1 (cut off is 10 or more).
    D3 gap 1, tier 3 (2), effort S: 2 x 2 x 1 / 1 = 4.0 -> wave 2 (cut off is 4 or more).
    D4 gap 2, tier 3 (2), effort L, Enhanced: 1 x 2 x 2 / 3 = 1.33 -> wave 3.
    D6 gap 0 is left out. Order D1, D2, D3, D4. Wave counts 2, 1, 1.
  Standard coverage:
    CSF PR.PS: D1 D 1.0 x 1/4 = 0.25, D2 P 0.5 x 1/4 = 0.125. Indicative 25.0, source backed 25.0, best control D1.
    ISO A.8.9: D2 P 0.125, D6 J 0.25 x 4/4 = 0.25, D5 D row is ignored because D5 is not applicable.
               Indicative 25.0, source backed 0.0, best control D6, two mapped controls.
    CIS 4:     D6 D 1.0 x 4/4 = 1.0, D3 P 0.5 x 2/4 = 0.25. Indicative 100.0, source backed 100.0.
    CCM CEK is NOT VERIFIED and is excluded, never scored.

----------------------------------------------------------------------------------------------------------
FIXTURE 3 (hand3.json): group roll up. unanswered_as is 2.
  ALPHA: profile G, managed model, six controls (G6 Enhanced M;G applies). Answers 2, 2, blank, 2, 2, 2 and the blank counts as 2.
         Every effective maturity is 2. Domain F1 and F2 mean 2.0 = 50.0 percent. Overall 50.0, met 0.0, answered 5 of 6 = 83.3.
         Accountable under the managed model: G1 vendor, G2 group.
  BETA:  profile S, five Baseline controls (G6 does not apply), all 3. Domains 75.0, overall 75.0, met 100.0, complete 100.0.
  Group: plain mean of the property percentages (50.0 + 75.0) / 2 = 62.5. Control weighted would be (6 x 2 + 5 x 3) / 11 = 2.4545 -> 61.4.
         Met: (0.0 + 100.0) / 2 = 50.0. Domain F1 mean (50.0 + 75.0) / 2 = 62.5 and F2 the same.
  Jurisdiction (AE configured): OBL-AE-1 has tag AE-DXB which is a child of AE so it is in scope.
    ALPHA: G1, G2, G6 all 2 -> mean 2.0 = 50.0, none met, not ready. BETA: G6 not applicable so G1 and G2 count: mean 3.0 = 75.0, ready.
    OBL-AE-2 (AE-DIFC) names T5, which is not active, so it is out of scope. OBL-US-1 (US-NY) is not configured so it is out of scope.
    OBL-AE-3 is SECONDARY so it is tracking. With T5 switched on, OBL-AE-2 enters the scored set (two scored, one out of scope).
  Standard (ALPHA, universe of five CSF categories PR.AA, PR.DS, ID.AM, GV.SC, DE.CM):
    PR.AA: G1 D 1.0 x 2/4 = 0.5 -> 50.0 and 50.0. PR.DS: G4 P 0.5 x 2/4 = 0.25 -> indicative 25.0, source backed 0.0.
    Universe view: source backed (0.5 + 0.0) / 5 = 0.10 = 10.0, indicative (0.5 + 0.25) / 5 = 0.15 = 15.0.
    Reached 2, unreached 3: ID.AM, GV.SC, DE.CM.
"""
import copy
import unittest

import support  # noqa: F401  (puts src/ on the path)
import applicability
import ingest_hissrat
import roadmap
import score
import settings
from support import load_hand, run_hand


def std_rows(fx, rows, cfg, universe=None):
    sv = score.standard_view(rows, fx["crosswalk_rows"], cfg, universe)
    return sv, {"%s|%s" % (r["framework"], r["target_id"]): r for r in sv["rows"]}


class HandFixtureOne(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = load_hand("hand1")
        cls.exp = cls.fx["expected"]
        cls.cfg, cls.app, cls.rows = run_hand(cls.fx, "HAND1")
        cls.by_id = {r["control_id"]: r for r in cls.rows}
        cls.doms = {d["domain"]: d for d in score.domain_scores(cls.rows)}

    def test_control_maturity_and_met(self):
        self.assertEqual(len(self.rows), 5)
        for cid, m in self.exp["control_maturity"].items():
            self.assertEqual(self.by_id[cid]["maturity"], m, cid)
            self.assertEqual(self.by_id[cid]["met"], self.exp["control_met"][cid], cid)

    def test_blank_answer_counts_as_zero_and_is_flagged_unanswered(self):
        self.assertEqual(self.by_id["C5"]["answered"], "no")
        self.assertEqual(self.by_id["C5"]["maturity"], 0)

    def test_domain_scores(self):
        self.assertEqual(sorted(self.doms), ["F4", "H02", "H07"])
        for d, want in self.exp["domains"].items():
            for k, v in want.items():
                self.assertAlmostEqual(self.doms[d][k], v, places=6, msg="%s %s" % (d, k))

    def test_property_score(self):
        prop = score.property_score(self.rows, list(self.doms.values()))
        for k, v in self.exp["property"].items():
            self.assertAlmostEqual(prop[k], v, places=6, msg=k)

    def test_standard_coverage_numbers(self):
        _, by = std_rows(self.fx, self.rows, self.cfg)
        for key, want in self.exp["standard"].items():
            self.assertIn(key, by)
            self.assertEqual(by[key]["indicative_pct"], want["indicative_pct"], key + " indicative")
            self.assertEqual(by[key]["source_backed_pct"], want["source_backed_pct"], key + " source backed")
        self.assertEqual(by["CIS|5"]["direct_rows"], 0)

    def test_framework_summary_without_universe(self):
        sv, _ = std_rows(self.fx, self.rows, self.cfg)
        fw = {f["framework"]: f for f in sv["frameworks"]}
        for k, v in self.exp["framework_summary"]["ISO27001"].items():
            self.assertEqual(fw["ISO27001"][k], v, k)

    def test_jurisdiction_readiness(self):
        res = score.jurisdiction_readiness(self.fx["obligation_rows"], self.rows, self.cfg)
        rows = {r["obligation_id"]: r for r in res["rows"]}
        for oid, want in self.exp["jurisdiction"].items():
            if oid == "IN":
                continue
            for k, v in want.items():
                self.assertEqual(rows[oid][k], v, "%s %s" % (oid, k))
        self.assertEqual(rows["OBL-IN-3"]["readiness_pct"], "")
        summ = {s["jurisdiction"]: s for s in res["summary"]}["IN"]
        for k, v in self.exp["jurisdiction"]["IN"].items():
            self.assertEqual(summ[k], v, k)


class HandFixtureTwo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = load_hand("hand2")
        cls.exp = cls.fx["expected"]
        cls.raw = cls.fx["config"]
        cls.cfg0 = settings.property_settings(cls.raw, "P")
        cls.app0 = applicability.filter_controls(cls.fx["controls"], cls.cfg0)
        scope = ingest_hissrat.select_scope(cls.fx["systems"], ["P"])
        cls.caps_all = ingest_hissrat.derive_caps(cls.fx["findings"], scope, cls.fx["families"], cls.cfg0["finding_caps"])
        applic = set(applicability.applicable_ids(cls.app0))
        cls.caps = {k: v for k, v in cls.caps_all.items() if k in applic}
        cls.cfg, cls.app, cls.rows = run_hand(cls.fx, "P", caps=cls.caps)
        cls.by_id = {r["control_id"]: r for r in cls.rows}
        cls.doms = {d["domain"]: d for d in score.domain_scores(cls.rows)}

    def test_trigger_makes_enhanced_control_mandatory_for_s(self):
        self.assertEqual(applicability.applicable_ids(self.app0), self.exp["applicable"])
        reason = {r["control_id"]: r["reason"] for r in self.app0}
        self.assertIn("trigger T4", reason["D4"])
        self.assertIn("no trigger active", reason["D5"])

    def test_caps_and_tiers(self):
        for cid, cap in self.exp["caps"].items():
            self.assertEqual(self.caps[cid]["cap"], cap, cid)
            self.assertEqual(sorted(self.caps[cid]["tiers"]), self.exp["cap_tiers"][cid], cid)
        self.assertNotIn("S3", self.caps["D3"]["systems"])
        self.assertNotIn("S1", self.caps["D3"]["systems"], "a Low finding sets no cap and adds no system")

    def test_effective_maturity_never_raised_by_cap(self):
        for cid, m in self.exp["control_maturity"].items():
            self.assertEqual(self.by_id[cid]["maturity"], m, cid)
            self.assertEqual(self.by_id[cid]["capped"], self.exp["control_capped"][cid], cid)
        self.assertNotIn("D5", self.by_id, "an answer for an inapplicable control is not scored")

    def test_domain_and_property_scores(self):
        for d, want in self.exp["domains"].items():
            for k, v in want.items():
                self.assertAlmostEqual(self.doms[d][k], v, places=6, msg="%s %s" % (d, k))
        prop = score.property_score(self.rows, list(self.doms.values()))
        for k, v in self.exp["property"].items():
            self.assertAlmostEqual(prop[k], v, places=6, msg=k)

    def test_roadmap_priority_order_and_waves(self):
        items = roadmap.build_roadmap(self.rows, self.fx["controls_by_id"], self.caps, self.cfg)
        self.assertEqual([i["control_id"] for i in items], [e["control_id"] for e in self.exp["roadmap"]])
        for item, want in zip(items, self.exp["roadmap"]):
            self.assertAlmostEqual(item["priority"], want["priority"], places=2, msg=item["control_id"])
            self.assertEqual(item["wave"], want["wave"], item["control_id"])
            self.assertEqual(item["tier"], want["tier"], item["control_id"])
            self.assertEqual(item["gap"], want["gap"], item["control_id"])
        waves = {str(w["wave"]): w["items"] for w in roadmap.wave_summary(items, self.cfg)}
        self.assertEqual(waves, self.exp["wave_counts"])
        self.assertEqual([i["rank"] for i in items], [1, 2, 3, 4])

    def test_standard_coverage_ignores_inapplicable_and_not_verified(self):
        _, by = std_rows(self.fx, self.rows, self.cfg)
        for key, want in self.exp["standard"].items():
            for k, v in want.items():
                self.assertEqual(by[key][k], v, "%s %s" % (key, k))
        cek = by["CCM|CEK"]
        self.assertEqual(cek["state"], "excluded (NOT VERIFIED target)")
        self.assertEqual(cek["indicative_pct"], "")


class HandFixtureThree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = load_hand("hand3")
        cls.exp = cls.fx["expected"]
        cls.alpha = run_hand(cls.fx, "ALPHA")
        cls.beta = run_hand(cls.fx, "BETA")

    def _prop(self, run):
        cfg, app, rows = run
        doms = score.domain_scores(rows)
        return {"property": cfg["property"], "overall": score.property_score(rows, doms), "domains": doms}

    def test_property_level_numbers(self):
        for name, run in (("ALPHA", self.alpha), ("BETA", self.beta)):
            exp = self.exp[name]
            cfg, app, rows = run
            self.assertEqual(len(rows), exp["applicable"], name)
            by = {r["control_id"]: r for r in rows}
            for cid, m in exp["control_maturity"].items():
                self.assertEqual(by[cid]["maturity"], m, "%s %s" % (name, cid))
            p = self._prop(run)
            for d, want in exp["domains"].items():
                got = {x["domain"]: x for x in p["domains"]}[d]
                self.assertEqual(got["maturity_pct"], want["maturity_pct"], "%s %s" % (name, d))
            for k, v in exp["property"].items():
                self.assertEqual(p["overall"][k], v, "%s %s" % (name, k))

    def test_unanswered_as_setting_is_used(self):
        by = {r["control_id"]: r for r in self.alpha[2]}
        self.assertEqual(by["G3"]["answered"], "no")
        self.assertEqual(by["G3"]["maturity"], 2)

    def test_accountable_party_follows_operating_model(self):
        app = {a["control_id"]: a for a in self.alpha[1]}
        for cid, who in self.exp["ALPHA"]["accountable"].items():
            self.assertEqual(app[cid]["accountable"], who)
        beta = {a["control_id"]: a for a in self.beta[1]}
        self.assertEqual(beta["G1"]["accountable"], "property", "owned is the default operating model")
        self.assertEqual(beta["G6"]["applicable"], "no")

    def test_group_roll_up_is_plain_mean_of_properties(self):
        g = score.group_maturity([self._prop(self.alpha), self._prop(self.beta)])
        want = self.exp["group"]
        self.assertEqual(g["group_maturity_pct"], want["group_maturity_pct"])
        self.assertEqual(g["group_met_pct"], want["group_met_pct"])
        self.assertEqual(g["domain_mean_pct"], want["domain_mean_pct"])
        self.assertEqual(g["domain_matrix"]["F1"], want["domain_matrix_F1"])
        self.assertNotEqual(g["group_maturity_pct"], 61.4, "must not be the control weighted mean")

    def test_jurisdiction_parent_child_trigger_and_tracking(self):
        for name, run in (("ALPHA", self.alpha), ("BETA", self.beta)):
            cfg, app, rows = run
            res = score.jurisdiction_readiness(self.fx["obligation_rows"], rows, cfg)
            exp = self.exp[name]["jurisdiction"]
            row = {r["obligation_id"]: r for r in res["rows"]}["OBL-AE-1"]
            for k, v in exp["OBL-AE-1"].items():
                self.assertEqual(row[k], v, "%s %s" % (name, k))
            summ = {s["jurisdiction"]: s for s in res["summary"]}["AE"]
            for k, v in exp["summary"].items():
                self.assertEqual(summ[k], v, "%s %s" % (name, k))
            ids = {r["obligation_id"] for r in res["rows"]}
            self.assertNotIn("OBL-US-1", ids)
            self.assertNotIn("OBL-AE-2", ids)
        res = score.jurisdiction_readiness(self.fx["obligation_rows"], self.alpha[2], self.alpha[0])
        self.assertEqual(len(res["out_of_scope"]), self.exp["ALPHA"]["jurisdiction"]["out_of_scope"])

    def test_trigger_switched_on_brings_obligation_into_scope(self):
        cfg, app, rows = run_hand(self.fx, "ALPHA", config_override={"triggers": ["T5"]})
        res = score.jurisdiction_readiness(self.fx["obligation_rows"], rows, cfg)
        want = self.exp["alpha_with_t5"]
        self.assertEqual(res["overall"]["obligations_scored"], want["obligations_scored"])
        self.assertEqual(len(res["out_of_scope"]), want["out_of_scope"])

    def test_standard_view_with_clause_universe(self):
        cfg, app, rows = self.alpha
        sv, by = std_rows(self.fx, rows, cfg, self.fx["universe_map"])
        want = self.exp["standard_alpha"]
        for key in ("CSF|PR.AA", "CSF|PR.DS"):
            self.assertEqual(by[key]["indicative_pct"], want[key]["indicative_pct"], key)
            self.assertEqual(by[key]["source_backed_pct"], want[key]["source_backed_pct"], key)
        csf = {f["framework"]: f for f in sv["frameworks"]}["CSF"]
        for k, v in want["summary"].items():
            self.assertEqual(csf[k], v, k)
        unreached_rows = [r for r in sv["rows"] if r["state"] == "not reached by any HISS control"]
        self.assertEqual(sorted(r["target_id"] for r in unreached_rows), sorted(want["summary"]["unreached"]))


if __name__ == "__main__":
    unittest.main()
