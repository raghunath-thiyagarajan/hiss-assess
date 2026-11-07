"""Pipeline smoke tests, written outputs, dashboard rules (single file, no external address) and no network use."""
import ast
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

import support
import dashboard
import pipeline
import report
import settings
from test_ingest_sensitivity import simulated_assessment

CAT = support.real_catalogue()

DATE_RX = re.compile(r"\b(?:19|20)\d\d-\d{2}-\d{2}\b|\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
                     r"September|October|November|December)\s+\d{4}\b|\b(?:January|February|March|April|June|July|August|"
                     r"September|October|November|December)\s+\d{4}\b")
NETWORK_MODULES = {"socket", "ssl", "urllib", "http", "ftplib", "smtplib", "telnetlib", "xmlrpc", "requests", "httpx",
                   "aiohttp", "poplib", "imaplib", "socketserver", "webbrowser"}


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def real_results():
    cfg = settings.property_settings(support.real_config(), "PROP-A")
    app, answers, caps = simulated_assessment(cfg)
    universe = support.catalogue.load_clause_universe(CAT)
    res = pipeline.run_property(CAT, cfg, answers, universe=universe, assessment_name="assessment_PROP-A.csv")
    return res


class DashboardRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = real_results()
        cls.html = dashboard.render_dashboard(cls.res)
        with open(dashboard.TEMPLATE, encoding="utf-8") as fh:
            cls.template = fh.read()

    def external_references(self, text):
        """Every place where an external address would be fetched: src, href, url(), @import, action, srcset, CSS and JS loaders."""
        found = []
        patterns = [
            r"""\b(?:src|href|action|poster|data|srcset)\s*=\s*["']?\s*(?:https?:)?//""",
            r"""url\(\s*["']?\s*(?:https?:)?//""",
            r"""@import\s+(?:url\()?\s*["']?\s*(?:https?:)?//""",
            r"""<link\b""",
            r"""<script\b[^>]*\bsrc\s*=""",
            r"""<iframe\b|<embed\b|<object\b""",
        ]
        for p in patterns:
            for m in re.finditer(p, text, re.I):
                found.append(text[m.start():m.start() + 60])
        return found

    def test_no_external_url_in_src_href_or_css(self):
        self.assertEqual(self.external_references(self.html), [])
        self.assertEqual(self.external_references(self.template), [])

    def test_no_http_addresses_at_all(self):
        """Stricter than needed: even text strings carry no http or https address."""
        self.assertEqual(re.findall(r"https?://[^\s\"'<>]{1,40}", self.html), [])

    def test_no_script_that_loads_or_sends_over_the_network(self):
        for word in ("fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon", "importScripts", "EventSource", "import("):
            self.assertNotIn(word, self.html, word)

    def test_single_self_contained_file(self):
        self.assertTrue(self.html.lstrip().lower().startswith("<!doctype html"))
        self.assertGreaterEqual(len(re.findall(r"<style\b", self.html)), 1)
        self.assertGreaterEqual(len(re.findall(r"<script\b", self.html)), 1)
        self.assertNotIn("__PAYLOAD__", self.html)
        self.assertLess(len(self.html.encode("utf-8")), 5 * 1024 * 1024)

    def test_payload_is_valid_json_and_carries_the_assumed_labels(self):
        m = re.search(r'<script id="payload" type="application/json">(.*?)</script>', self.html, re.S)
        self.assertIsNotNone(m)
        data = json.loads(m.group(1).replace("<\\/", "</"))
        self.assertEqual(data["author"], "Raghunath Thiyagarajan")
        self.assertIn("assumed", data["assumptions"]["note"].lower())
        self.assertEqual(data["input"]["tag"], "A26")
        self.assertNotIn("assessment_file", data["input"])

    def test_page_follows_system_theme_and_phone_width(self):
        self.assertIn("prefers-color-scheme", self.html)
        self.assertIn('name="viewport"', self.html)


class WrittenOutputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = os.path.join(cls.tmp.name, "out")
        cls.res = real_results()
        cls.names = report.write_outputs(cls.res, cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_ten_output_files_are_written(self):
        self.assertEqual(len(self.names), 10)
        for n in self.names:
            self.assertTrue(os.path.getsize(os.path.join(self.out, n)) > 0, n)

    def test_dashboard_is_the_only_html_and_no_asset_files_are_written(self):
        files = sorted(os.listdir(self.out))
        self.assertEqual([f for f in files if f.endswith(".html")], ["dashboard.html"])
        for ext in (".css", ".js", ".png", ".svg", ".woff", ".woff2", ".ttf"):
            self.assertEqual([f for f in files if f.endswith(ext)], [], ext)

    def test_outputs_carry_no_absolute_paths_or_dates(self):
        bad = []
        for n in os.listdir(self.out):
            with open(os.path.join(self.out, n), encoding="utf-8") as fh:
                text = fh.read()
            for needle in (support.ROOT, self.tmp.name, "/tmp/", "/home/", "/Users/", "C:\\\\", "C:/"):
                if needle in text:
                    bad.append((n, "path", needle))
            m = DATE_RX.search(text)
            if m:
                bad.append((n, "date", m.group(0)))
        self.assertEqual(bad, [])

    def test_results_json_is_ascii_and_consistent_with_csv(self):
        with open(os.path.join(self.out, "results.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["toolkit"], "HISS-Assess")
        self.assertEqual(data["catalogue"]["controls"], 80)
        lines = read_text(os.path.join(self.out, "control_scores.csv")).strip().splitlines()
        self.assertEqual(len(lines) - 1, data["overall"]["controls"])
        self.assertEqual(data["overall"]["controls"], 80, "profile M with no trigger filter applies all 80")

    def test_gap_report_labels_simulated_input(self):
        text = read_text(os.path.join(self.out, "gap_report.md"))
        self.assertIn("A26", text)
        self.assertIn("simulated", text.lower())

    def test_pipeline_is_deterministic(self):
        again = real_results()
        self.assertEqual(json.dumps(again, sort_keys=True), json.dumps(self.res, sort_keys=True))


class CommandLineRun(unittest.TestCase):
    def test_run_all_on_sample_catalogue(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, docs = os.path.join(tmp, "out"), os.path.join(tmp, "docs")
            cmd = [sys.executable, "-B", os.path.join(support.ROOT, "run_all.py"), "--property", "SAMPLEHOTEL",
                   "--config", support.SAMPLE_CONFIG, "--catalogue", support.SAMPLE_CATALOGUE,
                   "--inputs-dir", support.SAMPLE_INPUTS, "--hissrat-dir", os.path.join(support.SAMPLE_INPUTS, "hissrat"),
                   "--out-dir", out, "--docs-dir", docs]
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            proc = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=120, env=env)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue(os.path.isfile(os.path.join(out, "dashboard.html")))
            self.assertTrue(os.path.isfile(os.path.join(docs, "HISS_Standard_v1.md")))
            self.assertNotIn(tmp, proc.stdout, "console output shows no absolute path")
            res = json.loads(read_text(os.path.join(out, "results.json")))
            self.assertEqual(res["property"]["name"], "SAMPLEHOTEL")
            self.assertEqual(res["hissrat"]["all_systems"]["systems"], 4)
            self.assertEqual(res["family_coverage"]["mapped"], 12)

    def test_missing_questionnaire_writes_blank_template_and_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            inputs = os.path.join(tmp, "inputs")
            os.makedirs(inputs)
            cmd = [sys.executable, "-B", os.path.join(support.ROOT, "run_all.py"), "--property", "NEWHOTEL",
                   "--config", support.SAMPLE_CONFIG, "--catalogue", support.SAMPLE_CATALOGUE, "--inputs-dir", inputs,
                   "--out-dir", os.path.join(tmp, "out"), "--docs-dir", os.path.join(tmp, "docs"), "--no-hissrat"]
            proc = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertTrue(os.path.isfile(os.path.join(inputs, "assessment_NEWHOTEL.csv")))
            self.assertTrue(os.path.isfile(os.path.join(inputs, "assessment_NEWHOTEL_questions.csv")))
            self.assertFalse(os.path.exists(os.path.join(tmp, "out", "dashboard.html")))


class SampleCatalogue(unittest.TestCase):
    def test_sample_catalogue_is_valid_in_the_exact_schema(self):
        cat = support.catalogue.load_catalogue(support.SAMPLE_CATALOGUE)
        res = support.catalogue.validate_catalogue(cat)
        self.assertEqual(res["errors"], [])
        self.assertEqual(len(cat["controls"]), 12)
        self.assertEqual(len({c["domain"] for c in cat["controls"]}), 4)

    def test_missing_catalogue_file_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(support.catalogue.CatalogueError):
                support.catalogue.load_catalogue(tmp)

    def test_validator_catches_a_d_row_without_source_and_a_bad_obligation_status(self):
        import copy
        cat = copy.deepcopy(support.catalogue.load_catalogue(support.SAMPLE_CATALOGUE))
        cat["crosswalk"][0]["source"] = ""
        cat["crosswalk"][0]["strength"] = "D"
        cat["obligations"][0]["status"] = "NOT VERIFIED"
        errors = support.catalogue.validate_catalogue(cat)["errors"]
        self.assertTrue(any("needs a named source" in e for e in errors), errors)
        self.assertTrue(any("status must be VERIFIED or SECONDARY" in e for e in errors), errors)


class StandardLibraryOnlyAndOffline(unittest.TestCase):
    def test_sources_import_only_the_standard_library_and_no_network_module(self):
        local = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(support.SRC_DIR, "*.py"))}
        stdlib = set(sys.stdlib_module_names)
        files = sorted(glob.glob(os.path.join(support.SRC_DIR, "*.py"))) + [os.path.join(support.ROOT, "run_all.py")]
        self.assertGreaterEqual(len(files), 14)
        offenders = []
        for path in files:
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), path)
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module.split(".")[0]]
                for n in names:
                    if n in NETWORK_MODULES or not (n in stdlib or n in local):
                        offenders.append((os.path.basename(path), n))
        self.assertEqual(offenders, [])

    def test_render_standard_matches_catalogue_counts(self):
        import render_standard
        text = render_standard.render_standard(CAT, support.catalogue.load_domain_names(CAT))
        for c in CAT["controls"]:
            self.assertIn(c["control_id"], text)
        self.assertGreaterEqual(len(re.findall(r"HISS-(?:F[1-6]|H\d\d)-\d\d", text)), 80)


if __name__ == "__main__":
    unittest.main()
