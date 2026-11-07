"""Schema and integrity of the real catalogue (catalogue/), the crosswalk rules and the obligations rules."""
import os
import re
import unittest
from collections import Counter, defaultdict

import support
import catalogue as cat_mod
import score
from common import DOMAIN_ORDER, read_json

CAT = support.real_catalogue()
CONTROLS = CAT["controls"]
CROSSWALK = CAT["crosswalk"]
OBLIGATIONS = CAT["obligations"]
UNIVERSE = cat_mod.load_clause_universe(CAT)
VERIFIED_CSF = {u["id"] for u in UNIVERSE["CSF"]}


class CatalogueSchema(unittest.TestCase):
    def test_validate_full_has_no_errors(self):
        res = cat_mod.validate_catalogue(CAT, full=True)
        self.assertEqual(res["errors"], [], "\n".join(res["errors"][:10]))

    def test_validate_full_has_no_warnings(self):
        """The only warning allowed is the unused trigger one: no control uses T1 (a design choice, see the T1 test)."""
        res = cat_mod.validate_catalogue(CAT, full=True)
        others = [w for w in res["warnings"] if not w.startswith("trigger T1 is used by no control")]
        self.assertEqual(others, [], "\n".join(others[:10]))

    def test_eighty_controls(self):
        self.assertEqual(len(CONTROLS), 80)

    def test_control_ids_unique_and_well_formed(self):
        ids = [c["control_id"] for c in CONTROLS]
        self.assertEqual(len(ids), len(set(ids)))
        for cid in ids:
            self.assertRegex(cid, cat_mod.CONTROL_ID_RX.pattern)

    def test_domains_valid_and_match_control_id(self):
        for c in CONTROLS:
            self.assertIn(c["domain"], DOMAIN_ORDER, c["control_id"])
            self.assertEqual(c["control_id"].split("-")[1], c["domain"], c["control_id"])
        self.assertEqual(set(c["domain"] for c in CONTROLS), set(DOMAIN_ORDER), "all 16 domains are used")

    def test_domain_names_defined_for_every_domain(self):
        names = cat_mod.load_domain_names(CAT)
        for d in DOMAIN_ORDER:
            self.assertTrue(names.get(d), d)

    def test_four_to_six_controls_per_domain(self):
        counts = Counter(c["domain"] for c in CONTROLS)
        for d in DOMAIN_ORDER:
            self.assertTrue(4 <= counts[d] <= 6, "%s has %d controls" % (d, counts[d]))

    def test_each_reality_has_three_or_more_controls(self):
        defined = {r["reality_id"] for r in CAT["realities"]}
        self.assertEqual(defined, {"R1", "R2", "R3", "R4", "R5", "R6", "R7"})
        for rid in sorted(defined):
            n = sum(1 for c in CONTROLS if rid in c["reality_list"])
            self.assertGreaterEqual(n, 3, "reality %s is addressed by %d controls" % (rid, n))

    def test_evidence_has_at_least_two_artefacts(self):
        for c in CONTROLS:
            self.assertGreaterEqual(len(c["evidence_list"]), 2, c["control_id"])
            self.assertEqual(len(c["evidence_list"]), len(set(c["evidence_list"])), "duplicate artefact in " + c["control_id"])

    def test_levels_profiles_and_triggers_are_consistent(self):
        for c in CONTROLS:
            cid = c["control_id"]
            self.assertIn(c["level"], ("Baseline", "Enhanced"), cid)
            if c["level"] == "Baseline":
                self.assertEqual(set(c["profile_list"]), {"S", "M", "G"}, cid)
                self.assertEqual(c["trigger_list"], [], "a trigger on a Baseline control has no effect: " + cid)
            else:
                self.assertNotIn("S", c["profile_list"], cid)
                self.assertTrue(set(c["profile_list"]) <= {"M", "G"}, cid)
            for t in c["trigger_list"]:
                self.assertIn(t, ("T1", "T2", "T3", "T4", "T5"), cid)

    def test_owner_values_are_valid_for_all_operating_models(self):
        for c in CONTROLS:
            for f in ("owner_owned", "owner_managed", "owner_franchised"):
                self.assertIn(c[f], ("group", "property", "vendor", "franchisee"), "%s %s" % (c["control_id"], f))

    def test_text_fields_are_filled_and_basis_is_valid(self):
        for c in CONTROLS:
            for f in ("title", "objective", "requirement", "rationale", "assessment_question", "c1_link"):
                self.assertTrue(c[f].strip(), "%s %s" % (c["control_id"], f))
            self.assertIn(c["basis"], ("sourced", "derived", "judgement"), c["control_id"])

    def test_requirements_use_shall(self):
        for c in CONTROLS:
            self.assertRegex(c["requirement"], r"\bshall\b", c["control_id"])

    def test_cross_references_resolve(self):
        ids = {c["control_id"] for c in CONTROLS}
        for o in OBLIGATIONS:
            self.assertTrue(set(o["control_list"]) <= ids, o["obligation_id"])
        for f in CAT["families"]:
            self.assertTrue(set(f["control_list"]) <= ids, f["family_key"])
        for r in CAT["requirements"]:
            self.assertTrue(set(r["control_list"]) <= ids, r["req_id"])
        for x in CROSSWALK:
            self.assertIn(x["control_id"], ids)

    def test_twelve_families_each_reach_a_control_and_match_the_ingest_patterns(self):
        self.assertEqual(len(CAT["families"]), 12)
        for f in CAT["families"]:
            self.assertTrue(f["control_list"], f["family_key"])
        patterns = read_json(os.path.join(support.CONFIG_DIR, "family_patterns.json"))["families"]
        self.assertEqual({p["key"] for p in patterns}, {f["family_key"] for f in CAT["families"]})


class CrosswalkRules(unittest.TestCase):
    def test_no_direct_row_without_a_named_source(self):
        bad = [x for x in CROSSWALK if x["strength"] == "D" and not x["source"].strip()]
        self.assertEqual(bad, [])

    def test_direct_rows_point_to_verified_targets(self):
        bad = [(x["control_id"], x["target_id"]) for x in CROSSWALK if x["strength"] == "D" and x["target_status"] != "VERIFIED"]
        self.assertEqual(bad, [])

    def test_no_chained_direct_rows(self):
        """Chaining through another framework never produces D (E31): a D row may not be described as a chain."""
        rx = re.compile(r"\bchain(ed|ing)?\b|\bvia\s+(CSF|ISO|CIS|PCI)", re.I)
        offenders = []
        for x in CROSSWALK:
            if x["strength"] != "D":
                continue
            text = " ".join((x["note"], x["source"]))
            if rx.search(text):
                offenders.append((x["control_id"], x["framework"], x["target_id"]))
        self.assertEqual(offenders, [])

    def test_strength_status_and_framework_values(self):
        for x in CROSSWALK:
            self.assertIn(x["strength"], ("D", "P", "J"))
            self.assertIn(x["target_status"], ("VERIFIED", "SECONDARY", "NOT VERIFIED"))
            self.assertIn(x["framework"], cat_mod.FRAMEWORKS)
            self.assertTrue(x["target_id"].strip())

    def test_row_caps_per_control(self):
        per = defaultdict(Counter)
        for x in CROSSWALK:
            per[x["control_id"]][x["framework"]] += 1
        for cid, counts in per.items():
            for fw, cap in cat_mod.ROW_CAPS.items():
                self.assertLessEqual(counts[fw], cap, "%s has %d %s rows" % (cid, counts[fw], fw))

    def test_every_control_has_iso_csf_and_cis_rows(self):
        have = defaultdict(set)
        for x in CROSSWALK:
            have[x["control_id"]].add(x["framework"])
        for c in CONTROLS:
            for fw in ("ISO27001", "CSF", "CIS"):
                self.assertIn(fw, have[c["control_id"]], "%s lacks %s" % (c["control_id"], fw))

    def test_no_duplicate_control_framework_target(self):
        keys = [(x["control_id"], x["framework"], x["target_id"]) for x in CROSSWALK]
        self.assertEqual(len(keys), len(set(keys)))

    def test_csf_targets_are_in_the_verified_22_categories(self):
        self.assertEqual(len(VERIFIED_CSF), 22)
        used = {x["target_id"] for x in CROSSWALK if x["framework"] == "CSF"}
        self.assertEqual(sorted(used - VERIFIED_CSF), [])

    def test_other_targets_are_in_the_clause_lists(self):
        for fw in ("ISO27001", "PCIDSS", "CIS", "CCM"):
            known = {score.clause_key(fw, u["id"]) for u in UNIVERSE[fw]}
            unknown = set()
            for x in CROSSWALK:
                if x["framework"] != fw:
                    continue
                key = score.clause_key(fw, x["target_id"])
                if fw == "ISO27001" and x["target_id"].startswith("C."):
                    continue  # management system clauses are scored apart from Annex A
                if key not in known:
                    unknown.add(x["target_id"])
            self.assertEqual(sorted(unknown), [], fw)

    def test_clause_list_sizes_match_the_standards(self):
        sizes = {fw: len(v) for fw, v in UNIVERSE.items()}
        self.assertEqual(sizes["ISO27001"], 93)
        self.assertEqual(sizes["PCIDSS"], 12)
        self.assertEqual(sizes["CIS"], 18)
        self.assertEqual(sizes["CSF"], 22)


class ObligationRules(unittest.TestCase):
    def test_every_row_has_verified_or_secondary_status(self):
        self.assertGreater(len(OBLIGATIONS), 0)
        for o in OBLIGATIONS:
            self.assertIn(o["status"], ("VERIFIED", "SECONDARY"), o["obligation_id"])

    def test_row_count_in_expected_range(self):
        self.assertTrue(30 <= len(OBLIGATIONS) <= 40, len(OBLIGATIONS))

    def test_ids_unique_and_tags_well_formed(self):
        ids = [o["obligation_id"] for o in OBLIGATIONS]
        self.assertEqual(len(ids), len(set(ids)))
        for o in OBLIGATIONS:
            self.assertRegex(o["jurisdiction"], cat_mod.JURISDICTION_RX.pattern)
            self.assertTrue(o["fact_ref"].strip(), o["obligation_id"])
            self.assertTrue(o["control_list"], o["obligation_id"])

    def test_secondary_rows_are_tracked_and_never_scored(self):
        secondary = [o for o in OBLIGATIONS if o["status"] == "SECONDARY"]
        self.assertGreater(len(secondary), 0, "the real catalogue is expected to carry SECONDARY rows")
        cfg = support.settings.property_settings(support.real_config(), "GROUP")
        cfg["jurisdictions"] = {o["jurisdiction"].split("-")[0]: "test" for o in OBLIGATIONS}
        cfg["triggers"] = ["T1", "T2", "T3", "T4", "T5"]
        rows = [{"control_id": c["control_id"], "maturity": 4} for c in CONTROLS]
        res = score.jurisdiction_readiness(OBLIGATIONS, rows, cfg)
        by = {r["obligation_id"]: r for r in res["rows"]}
        for o in secondary:
            r = by[o["obligation_id"]]
            self.assertEqual(r["row_type"], "tracking", o["obligation_id"])
            self.assertEqual(r["readiness_pct"], "", o["obligation_id"])
        scored_ids = {r["obligation_id"] for r in res["rows"] if r["row_type"] == "obligation"}
        self.assertFalse(scored_ids & {o["obligation_id"] for o in secondary})
        self.assertEqual(res["overall"]["obligations_scored"],
                         sum(1 for o in OBLIGATIONS if o["status"] == "VERIFIED"))
        self.assertEqual(res["overall"]["tracking_n"], len(secondary))


if __name__ == "__main__":
    unittest.main()
