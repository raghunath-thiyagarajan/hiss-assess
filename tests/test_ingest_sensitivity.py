"""HISS-RAT ingest (Capstone 1 totals, sample files), family coverage and the plus or minus 20 percent sensitivity."""
import math
import os
import random
import unittest

import support
import ingest_hissrat
import roadmap
import score
import sensitivity
import settings
from common import average_ranks, spearman

CAT = support.real_catalogue()
HISSRAT_DIR = os.path.join(support.INPUTS_DIR, "hissrat")
SAMPLE_HISSRAT = os.path.join(support.SAMPLE_INPUTS, "hissrat")


class IngestCapstoneOneTotals(unittest.TestCase):
    def test_anonymised_hissrat_input_reproduces_capstone_1_totals(self):
        if not os.path.isfile(os.path.join(HISSRAT_DIR, "systems_normalised.csv")):
            self.skipTest("inputs/hissrat/systems_normalised.csv is not present yet, "
                          "so the Capstone 1 totals (29 systems, 191 findings, 12 families) were not checked")
        cfg = settings.property_settings(support.real_config(), "GROUP")
        data = ingest_hissrat.load_hissrat(HISSRAT_DIR, cfg["hissrat"]["role_tier"])
        fams = ingest_hissrat.load_family_patterns()
        ingest_hissrat.classify_findings(data["findings"], fams)
        s = ingest_hissrat.summarise(data["systems"], data["findings"], fams)
        self.assertEqual(s["systems"], 29, "systems")
        self.assertEqual(s["findings_low_plus"], 191, "findings Low or above")
        self.assertEqual(s["families_defined"], 12)
        self.assertEqual(s["findings_without_family"], 0, "every Low or above finding falls in a family")
        # The tool counts families among Low or above findings only. LLMNR and cleartext protocols appear at Info
        # severity, so the 12 families of Capstone 1 are all reached only when Info rows are classified too.
        print("\n[ingest] families among Low or above findings: %d of 12" % s["families_found"])
        all_rows = support.read_csv(os.path.join(HISSRAT_DIR, "findings_normalised.csv")) \
            if os.path.isfile(os.path.join(HISSRAT_DIR, "findings_normalised.csv")) else []
        if all_rows:
            seen = {ingest_hissrat.classify_finding(r["plugin_name"], fams) for r in all_rows} - {""}
            self.assertEqual(len(seen), 12, "families reached at any severity: %s" % sorted(seen))
        self.assertGreaterEqual(s["families_found"], 10)

    def test_anonymised_labels_only(self):
        if not os.path.isfile(os.path.join(HISSRAT_DIR, "systems_normalised.csv")):
            self.skipTest("inputs/hissrat/ is not present yet")
        data = ingest_hissrat.load_hissrat(HISSRAT_DIR)
        for s in data["systems"]:
            self.assertRegex(s["system_id"], r"^[A-Z0-9]+(-[A-Z0-9]+)+$", s["system_id"])


class IngestSampleFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = ingest_hissrat.load_hissrat(SAMPLE_HISSRAT, {"sql": 1})
        cls.fams = ingest_hissrat.load_family_patterns()
        ingest_hissrat.classify_findings(cls.data["findings"], cls.fams)

    def test_systems_and_findings_counts(self):
        s = ingest_hissrat.summarise(self.data["systems"], self.data["findings"], self.fams)
        self.assertEqual(s["systems"], 4)
        self.assertEqual(s["findings_low_plus"], 7)
        self.assertEqual(s["by_severity"], {"Critical": 1, "High": 2, "Medium": 3, "Low": 1})
        self.assertEqual(s["findings_without_family"], 0)

    def test_findings_fall_back_to_plugins_column_without_findings_file(self):
        self.assertIn("plugins_low_plus", self.data["findings_source"])
        self.assertEqual(self.data["tier_source"], "risk_register.csv")

    def test_tiers_come_from_the_risk_register(self):
        tiers = {s["system_id"]: s["tier"] for s in self.data["systems"]}
        self.assertEqual(tiers["SAMPLEHOTEL-SQL-01"], 1)
        self.assertEqual(tiers["SAMPLEHOTEL-FD-01"], 2)
        self.assertEqual(tiers["SAMPLEHOTEL-DSK-01"], 4)

    def test_family_classification(self):
        fam = {f["plugin_name"]: f["family"] for f in self.data["findings"]}
        self.assertEqual(fam["Microsoft Message Queuing RCE (QueueJumper)"], "msmq_missing_patches")
        self.assertEqual(fam["SMB Signing not required"], "smb_signing")
        self.assertEqual(fam["TLS Version 1.0 Protocol Detection"], "legacy_tls_ssl")
        self.assertEqual(ingest_hissrat.classify_finding("Totally unrelated plugin", self.fams), "")

    def test_plugin_list_parser(self):
        out = ingest_hissrat.parse_plugin_list("High:A b | Low:C | Bogus:D | Medium:")
        self.assertEqual(out, [("High", "A b"), ("Low", "C")])
        self.assertEqual(ingest_hissrat.parse_plugin_list(""), [])

    def test_scope_selection(self):
        systems = self.data["systems"] + [{"system_id": "OTHER-SQL-01", "property": "OTHER", "tier": 1}]
        self.assertEqual(len(ingest_hissrat.select_scope(systems, ["samplehotel"])), 4)
        self.assertEqual(len(ingest_hissrat.select_scope(systems, "all")), 5)
        self.assertEqual(len(ingest_hissrat.select_scope(systems, None)), 5)
        self.assertEqual(len(ingest_hissrat.select_scope(systems, ["OTHER"])), 1)

    def test_missing_systems_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            ingest_hissrat.load_hissrat(os.path.join(support.FIXTURES, "does_not_exist"))


class FamilyCoverageV1(unittest.TestCase):
    def test_all_twelve_families_map_to_a_catalogue_control(self):
        cov = ingest_hissrat.family_coverage(CAT["families"], CAT["control_by_id"])
        self.assertEqual(cov["families"], 12)
        self.assertEqual(cov["mapped"], 12)
        self.assertEqual(cov["unmapped_families"], [])

    def test_family_with_only_unknown_controls_is_unmapped(self):
        rows = [{"family_key": "x", "control_ids": "NOPE"}, {"family_key": "y", "control_ids": "HISS-F4-01"}]
        cov = ingest_hissrat.family_coverage(rows, {"HISS-F4-01": {}})
        self.assertEqual(cov["unmapped_families"], ["x"])


# ------------------------------------------------------------------ Spearman and the plus or minus 20 percent check

def rank_with_ties(values):
    """Independent average rank (1 is smallest), written separately from common.average_ranks."""
    out = []
    for v in values:
        less = sum(1 for w in values if w < v)
        equal = sum(1 for w in values if w == v)
        out.append(less + (equal + 1) / 2.0)
    return out


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy)


def spearman_independent(a, b):
    return pearson(rank_with_ties(a), rank_with_ties(b))


class SpearmanHelper(unittest.TestCase):
    def test_textbook_example(self):
        iq = [86, 97, 99, 100, 101, 103, 106, 110, 112, 113]
        tv = [2, 20, 28, 27, 50, 29, 7, 17, 6, 12]
        self.assertAlmostEqual(spearman(iq, tv), -29.0 / 165.0, places=9)

    def test_perfect_and_reversed_rankings(self):
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)

    def test_ties_use_average_ranks(self):
        self.assertEqual(average_ranks([5, 1, 5, 3]), [3.5, 1.0, 3.5, 2.0])
        self.assertEqual(rank_with_ties([5, 1, 5, 3]), [3.5, 1.0, 3.5, 2.0])

    def test_undefined_cases_return_none(self):
        self.assertIsNone(spearman([1, 1, 1], [1, 2, 3]))
        self.assertIsNone(spearman([1], [1]))
        self.assertIsNone(spearman([1, 2], [1, 2, 3]))

    def test_matches_independent_implementation_on_random_data(self):
        rng = random.Random(7)
        for _ in range(25):
            a = [rng.randint(0, 6) for _ in range(12)]
            b = [rng.randint(0, 6) for _ in range(12)]
            if len(set(a)) < 2 or len(set(b)) < 2:
                continue
            self.assertAlmostEqual(spearman(a, b), spearman_independent(a, b), places=9)


def simulated_assessment(cfg):
    """Deterministic simulated answers for the real catalogue plus caps from synthetic scan findings (seed 26)."""
    rng = random.Random(26)
    app = support.applicability.filter_controls(CAT["controls"], cfg)
    answers = {}
    for a in app:
        if a["applicable"] == "yes":
            answers[a["control_id"]] = {"maturity": rng.choice([0, 1, 1, 2, 2, 2, 3, 3, 3, 4]), "evidence_ref": "x", "comment": ""}
    fam_controls = ingest_hissrat.family_to_controls(CAT["families"])
    systems = [{"system_id": "P-SQL-01", "property": "P", "tier": 1}, {"system_id": "P-FD-01", "property": "P", "tier": 2},
               {"system_id": "P-DSK-01", "property": "P", "tier": 4}]
    findings = [
        {"system_id": "P-SQL-01", "severity": "Critical", "family": "msmq_missing_patches", "plugin_name": "a"},
        {"system_id": "P-SQL-01", "severity": "High", "family": "remote_access_tools", "plugin_name": "b"},
        {"system_id": "P-FD-01", "severity": "Medium", "family": "smb_signing", "plugin_name": "c"},
        {"system_id": "P-FD-01", "severity": "High", "family": "legacy_tls_ssl", "plugin_name": "d"},
        {"system_id": "P-DSK-01", "severity": "Medium", "family": "llmnr", "plugin_name": "e"},
    ]
    caps = ingest_hissrat.derive_caps(findings, systems, fam_controls, cfg["finding_caps"])
    app_ids = set(support.applicability.applicable_ids(app))
    caps = {k: v for k, v in caps.items() if k in app_ids}
    return app, answers, caps


class WeightSensitivity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = settings.property_settings(support.real_config(), "PROP-A")
        app, answers, cls.caps = simulated_assessment(cls.cfg)
        cls.rows = score.score_controls(app, CAT["control_by_id"], answers, cls.caps, cls.cfg)

    def test_domain_ranking_is_stable_under_plus_minus_20_percent(self):
        base_items = roadmap.build_roadmap(self.rows, CAT["control_by_id"], self.caps, self.cfg)
        base = roadmap.domain_priority(base_items)
        domains = sorted(base)
        self.assertGreaterEqual(len(domains), 10)
        base_vec = [base[d] for d in domains]
        rhos = {}
        for family in ("level_weights", "tier_weights", "effort_weights"):
            for key in self.cfg[family]:
                for factor in (0.8, 1.2):
                    c2 = sensitivity.scale_setting(self.cfg, family, key, factor)
                    items = roadmap.build_roadmap(self.rows, CAT["control_by_id"], self.caps, c2)
                    dp = roadmap.domain_priority(items)
                    rho = spearman_independent(base_vec, [dp.get(d, 0.0) for d in domains])
                    rhos["%s.%s x%.1f" % (family, key, factor)] = rho
        self.assertEqual(len(rhos), 2 * (2 + 4 + 3))
        worst_name, worst = min(rhos.items(), key=lambda kv: kv[1])
        mean_rho = sum(rhos.values()) / len(rhos)
        print("\n[sensitivity] domain ranking Spearman rho over %d cases: min %.3f (%s), mean %.3f"
              % (len(rhos), worst, worst_name, mean_rho))
        self.assertGreaterEqual(worst, 0.8, "lowest rho %.3f for %s" % (worst, worst_name))

    def test_module_result_agrees_with_independent_calculation(self):
        rows = sensitivity.roadmap_sensitivity(self.rows, CAT["control_by_id"], self.caps, self.cfg)
        self.assertEqual(len(rows), 18)
        summ = sensitivity.summarise(rows, "domain_rho")
        self.assertGreaterEqual(summ["rho_min"], 0.8)
        self.assertLessEqual(summ["rho_max"], 1.0)
        self.assertEqual(summ["cases"], 18)
        print("[sensitivity] module summary: min %.3f, mean %.3f, max %.3f" % (summ["rho_min"], summ["rho_mean"], summ["rho_max"]))

    def test_unchanged_weights_give_rho_one(self):
        base_items = roadmap.build_roadmap(self.rows, CAT["control_by_id"], self.caps, self.cfg)
        c2 = sensitivity.scale_setting(self.cfg, "level_weights", "Baseline", 1.0)
        items = roadmap.build_roadmap(self.rows, CAT["control_by_id"], self.caps, c2)
        a, b = roadmap.domain_priority(base_items), roadmap.domain_priority(items)
        d = sorted(a)
        self.assertAlmostEqual(spearman_independent([a[k] for k in d], [b[k] for k in d]), 1.0)

    def test_strength_weight_sensitivity_on_framework_ranking(self):
        universe = support.catalogue.load_clause_universe(CAT)
        rows = sensitivity.framework_sensitivity(self.rows, CAT["crosswalk"], self.cfg, universe)
        self.assertEqual(len(rows), 6)
        vals = [r["framework_rho"] for r in rows if r["framework_rho"] is not None]
        self.assertTrue(vals)
        print("[sensitivity] framework ranking rho for strength weights: min %.3f" % min(vals))
        self.assertGreaterEqual(min(vals), 0.8)


if __name__ == "__main__":
    unittest.main()
