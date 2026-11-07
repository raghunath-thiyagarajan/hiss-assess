"""Privacy scan of the whole toolkit tree and writing rules for the README and docs.

Privacy rule (README, data privacy note): no raw addresses, host names, MAC addresses, user names, domain names
or licence keys in the repository, and no vendor, product or town names of the case data. The scan covers every
text file under the toolkit folder (code, catalogue, config, docs, fixtures, inputs and outputs) except this file,
which holds the patterns themselves.

The checks hold no real names. Vendor, product and town names are tested through SHA-256 digests of the lower case
word, so a name that comes back into the data is caught without the name being written here. A group or person
name can be checked on a local machine by listing one term per line in tests/private_terms.txt (untracked, see
.gitignore). Without that file the local check is skipped.

Writing rules: no em dash, no en dash and no serial comma. The serial comma check is a pattern (two comma separated
items followed by a comma and then and or or) and can be noisy, so any clear case in the README or docs fails.
"""
import glob
import hashlib
import os
import re
import sys
import unittest
import warnings

import support

THIS_FILE = os.path.abspath(__file__)
SKIP_DIRS = {"__pycache__", ".git", ".idea", ".vscode", "node_modules"}
TEXT_EXT = {".py", ".md", ".csv", ".json", ".html", ".txt", ".cff", ".gitignore", ".gitkeep", ""}

EM_DASH, EN_DASH = chr(0x2014), chr(0x2013)

IPV4_RX = re.compile(r"(?<![\w.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\w])")
MAC_RX = re.compile(r"(?<![0-9A-Fa-f:-])(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}(?![0-9A-Fa-f:-])"
                    r"|(?<![0-9A-Fa-f.])(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}(?![0-9A-Fa-f.])")
TLDS = "com|net|org|info|biz|edu|gov|int|in|io|co|ae|uk|us|eu|de|local|lan|corp|internal|intranet|home|hotel|hotels"
# Lower case host style names. CSF category codes such as DE.AE are upper case and are not matched.
HOST_RX = re.compile(r"(?<![\w@-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:%s)(?![\w-])" % TLDS)
PRIVATE_TERMS_FILE = os.path.join(os.path.dirname(THIS_FILE), "private_terms.txt")


def group_host_pattern(terms):
    """Pattern for host or mail style names that contain any of the given terms, in any case."""
    alt = "|".join(re.escape(t) for t in terms)
    return re.compile(r"[\w.-]*(?:%s)[\w-]*\.(?:%s|test)\b|@[\w-]*(?:%s)" % (alt, TLDS, alt), re.I)


def load_private_terms():
    try:
        with open(PRIVATE_TERMS_FILE, encoding="utf-8") as fh:
            return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    except OSError:
        return []


_TERMS = load_private_terms()
PRIVATE_TERM_RX = re.compile("|".join(re.escape(t) for t in _TERMS), re.I) if _TERMS else None
GROUP_HOST_RX = group_host_pattern(_TERMS) if _TERMS else None
EMAIL_RX = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
USER_PATH_RX = re.compile(r"[A-Za-z]:\\Users\\|/Users/\w|/home/\w")
LICENCE_KEY_RX = re.compile(r"\b[A-Z0-9]{4,6}(?:-[A-Z0-9]{4,6}){3,5}\b")

# Words that look like host names but are plain file or module names.
HOST_ALLOW = {"run_all.py", "e.g", "i.e"}

# SHA-256 digests of lower case words (vendor, product and town names of the case data) that must not appear.
BLOCKED_WORD_DIGESTS = frozenset([
    "466c9a8d67575253a446cf70cc4eed7281658f33fa61ecd4dc74d5a14e5143fc",
    "b01e26d3f5a5130b9d8d821c5a9d61e7c7d86df735f28bdcd6620fc58ac1006e",
    "69adfc225093b9b305f6ab564f37f4fcb3046e1388476c61ea74c8ac8c7b3579",
    "20bff4e3daba64b0c151ff275496b79a129db808edd1446362bc124de66b9dbb",
    "356ee5dc254f27d0591468e9c1e74fe6b114dc573919787dd179a14308e5178a",
    "0908381700da0b5e7ff80911a81de8788c6b9a7ff95d18b7030efdf62d8c28d1",
    "9be86f84d21c22b8064382f2d651838c101aa37bdbab6a719b890395bbfdfa94",
    "981666545f91f2a199633cc65b51a228d91427c7ddd19963821b492066a36455",
    "997fd09b1525ef0c91232cbba0b70b83b5ec4599be8e92c8e240e924192c3179",
    "7de8705f87003e1e016bb7f41b90bb8e8ccc373103ac269ea480cc7c34d4e2a4",
    "2ce750ad008722b2d48cbb65afe42c292f038de8a4fd893465c1536d3eced570",
    "d9944b5d2e617dc50d866eb732d1afac22ef1534e5de1dcb3185e715cf6f5468",
    "106549f5ce976b060f087845c862c01c15546e47a913631127da6e081d52420a",
    "9f0edca9fa11a46d6c009a2d46a6763f6ee8969106ce75822bd0af56505c46cb",
    "d984d54956a1107497e11450843636196a148a5cf74933a3ecaec5d1633bec0a",
    "183e1b1c9f919196c4bd50a1c3798d06439b1ae8df688bf711b6195dc8238917",
    "4ee4f59fb889694eac3229f66cf949547e3102db22505d4d208a8046a964bc09",
    "4af78fed4802a1e5f7837ee22e9d7dbc126a56ffd3cde344d28058239dd80522",
])
WORD_RX = re.compile(r"[A-Za-z]+")

# Names of AI products and typical generated text labels. The words are joined from parts so that this file does
# not carry them itself.
_AI_NAMES = ["chatg" + "pt", "opena" + "i", "cla" + "ude", "anthro" + "pic"]
AI_NAME_RX = re.compile("|".join(_AI_NAMES), re.I)
_AI = "a" + "i"
_LLM = "l" + "lm"
AI_LABEL_RX = re.compile(r"(?i)\b%s[- ]gener" % _AI + r"ated\b|\bgener" + r"ated by (?:an? )?(?:%s|%s)\b|\bas an %s\b" % (_AI, _LLM, _AI))

SERIAL_RX = re.compile(r"(?<![\w])[^,.;:!?\n()|]{1,60},[^,.;:!?\n()|]{1,60},\s+(?:and|or)\s")


_TREE_CACHE = {}


def text_files(root=None):
    """Text files under the toolkit folder as (path, text). Read once per run because the tree can be large."""
    root = root or support.ROOT
    if root not in _TREE_CACHE:
        _TREE_CACHE[root] = list(_read_tree(root))
    return _TREE_CACHE[root]


def _read_tree(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in sorted(files):
            path = os.path.join(base, name)
            if os.path.abspath(path) in (THIS_FILE, PRIVATE_TERMS_FILE):
                continue
            if os.path.splitext(name)[1].lower() not in TEXT_EXT:
                continue
            try:
                with open(path, encoding="utf-8") as fh:
                    yield path, fh.read()
            except (UnicodeDecodeError, OSError):
                continue


def rel(path):
    return os.path.relpath(path, support.ROOT)


def scan(rx, root=None, skip=None):
    hits = []
    for path, text in text_files(root):
        if skip and skip(path):
            continue
        for m in rx.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            hits.append("%s:%d %s" % (rel(path), line, m.group(0)[:50]))
    return hits


def digest(word):
    return hashlib.sha256(word.lower().encode("utf-8")).hexdigest()


def blocked_words(text):
    """Distinct words of the text whose digest is on the blocked list (the word itself is not reported)."""
    found = 0
    for w in set(WORD_RX.findall(text)):
        if digest(w) in BLOCKED_WORD_DIGESTS:
            found += 1
    return found


class PrivacyScan(unittest.TestCase):
    def test_scan_actually_covers_the_tree(self):
        files = [rel(p) for p, _ in text_files()]
        self.assertGreater(len(files), 30)
        for must in ("README.md", os.path.join("docs", "HISS_Standard_v1.md"), os.path.join("catalogue", "controls.csv"),
                     os.path.join("src", "score.py"), os.path.join("config", "assessment_config.json")):
            self.assertIn(must, files)

    def test_no_ipv4_addresses(self):
        self.assertEqual(scan(IPV4_RX), [])

    def test_no_mac_addresses(self):
        self.assertEqual(scan(MAC_RX), [])

    def test_no_domain_like_host_names(self):
        hits = [h for h in scan(HOST_RX) if h.split(" ", 1)[1] not in HOST_ALLOW]
        self.assertEqual(hits, [])

    def test_no_mail_addresses_and_no_private_terms(self):
        self.assertEqual(scan(EMAIL_RX), [])
        if GROUP_HOST_RX is not None:
            self.assertEqual(scan(GROUP_HOST_RX), [])
        if PRIVATE_TERM_RX is not None:
            self.assertEqual(scan(PRIVATE_TERM_RX), [])

    def test_no_user_home_paths_or_licence_keys(self):
        self.assertEqual(scan(USER_PATH_RX), [])
        self.assertEqual(scan(LICENCE_KEY_RX), [])

    def test_no_vendor_product_or_town_names(self):
        bad = [rel(p) for p, text in text_files() if blocked_words(text)]
        self.assertEqual(bad, [], "a blocked vendor, product or town name is back in these files")

    def test_system_labels_are_property_and_role_only(self):
        pat = re.compile(r"^PROP-[A-F]-[A-Z0-9]+-\d{2}$")
        sample = re.compile(r"^SAMPLEHOTEL-[A-Z0-9]+-\d{2}$")
        bad = []
        n = 0
        for sub in ("inputs", os.path.join("tests", "fixtures", "sample_inputs")):
            for path in glob.glob(os.path.join(support.ROOT, sub, "**", "systems_normalised.csv"), recursive=True):
                for row in support.read_csv(path):
                    n += 1
                    if not (pat.match(row["system_id"]) or sample.match(row["system_id"])):
                        bad.append((rel(path), row["system_id"]))
        self.assertGreater(n, 0)
        self.assertEqual(bad, [])

    def test_property_files_use_property_letters(self):
        names = [os.path.basename(p) for p in glob.glob(os.path.join(support.INPUTS_DIR, "assessment_*.csv"))]
        for n in names:
            core = n[len("assessment_"):-len(".csv")]
            if core.endswith("_questions"):
                core = core[:-len("_questions")]
            self.assertTrue(re.match(r"^(PROP-[A-F]|GROUP)$", core), n)

    def test_scanner_detects_what_it_should(self):
        """Self check so a silent pattern failure cannot hide a leak."""
        self.assertTrue(IPV4_RX.search("host at 192.0.2.15 here"))
        self.assertTrue(MAC_RX.search("aa:bb:cc:dd:ee:ff"))
        self.assertTrue(MAC_RX.search("aabb.ccdd.eeff"))
        self.assertTrue(HOST_RX.search("sql01.corp.local"))
        self.assertTrue(HOST_RX.search("see example.com now"))
        self.assertTrue(group_host_pattern(["example-group"]).search("mail.example-group.test"))
        self.assertTrue(LICENCE_KEY_RX.search("ABCD-1234-EFGH-5678"))
        self.assertFalse(IPV4_RX.search("PCI DSS v4.0.1 and 27001:2022"))
        self.assertFalse(HOST_RX.search("DE.AE and RS.CO and PR.AA"))
        self.assertFalse(HOST_RX.search("python run_all.py --help"))

    def test_word_digest_check_self_check(self):
        sample = "w" + "inhms"
        self.assertEqual(digest(sample), hashlib.sha256(sample.encode()).hexdigest())
        self.assertIn(digest(sample), BLOCKED_WORD_DIGESTS)
        self.assertEqual(blocked_words("The " + sample.upper() + "-01 server"), 1)
        self.assertEqual(blocked_words("A totally ordinary sentence about PMS and accounting"), 0)


def doc_files():
    paths = [os.path.join(support.ROOT, "README.md")] + sorted(glob.glob(os.path.join(support.DOCS_DIR, "*.md")))
    return [p for p in paths if os.path.isfile(p)]


class WritingRules(unittest.TestCase):
    def test_readme_and_docs_exist(self):
        names = [os.path.basename(p) for p in doc_files()]
        self.assertIn("README.md", names)
        self.assertIn("HISS_Standard_v1.md", names)

    def test_no_em_dash_or_en_dash_in_readme_and_docs(self):
        hits = []
        for p in doc_files():
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
            for ch, name in ((EM_DASH, "em dash"), (EN_DASH, "en dash")):
                for m in re.finditer(ch, text):
                    hits.append("%s:%d %s" % (rel(p), text.count("\n", 0, m.start()) + 1, name))
        self.assertEqual(hits, [])

    def test_no_em_dash_or_en_dash_anywhere_in_the_tree(self):
        hits = scan(re.compile("[%s%s]" % (EM_DASH, EN_DASH)))
        self.assertEqual(hits, [])

    def test_no_serial_comma_in_readme_and_docs(self):
        hits = []
        for p in doc_files():
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
            in_code = False
            for line in text.splitlines():
                if line.strip().startswith("```"):
                    in_code = not in_code
                elif not in_code:
                    for m in SERIAL_RX.finditer(line):
                        hits.append("%s: %s" % (rel(p), m.group(0).strip()[:80]))
        for h in hits:
            warnings.warn("possible serial comma: " + h)
            print("[warning] possible serial comma: " + h, file=sys.stderr)
        self.assertEqual(hits, [], "the pattern is quiet on this repository, so any hit is worth a look")

    def test_serial_comma_pattern_self_check(self):
        self.assertTrue(SERIAL_RX.search(", ".join(["controls", "domains"]) + ", and standards"))
        self.assertTrue(SERIAL_RX.search(", ".join(["red", "green"]) + ", or blue"))
        self.assertFalse(SERIAL_RX.search("controls, domains and standards"))
        self.assertFalse(SERIAL_RX.search("It rained, and we stayed"))

    def test_readme_names_the_author(self):
        with open(os.path.join(support.ROOT, "README.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("Raghunath Thiyagarajan", text)

    def test_no_ai_product_names_or_generated_text_labels_in_the_tree(self):
        self.assertEqual(scan(AI_NAME_RX), [])
        self.assertEqual(scan(AI_LABEL_RX), [])

    def test_ai_pattern_self_check(self):
        self.assertTrue(AI_NAME_RX.search("made with " + _AI_NAMES[0]))
        self.assertTrue(AI_LABEL_RX.search("This text was " + "gener" + "ated by " + _AI.upper()))
        self.assertFalse(AI_LABEL_RX.search("The report is generated from the catalogue"))

    def test_no_dates_in_readme_and_docs(self):
        rx = re.compile(r"\b(?:19|20)\d\d-\d{2}-\d{2}\b|\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
                        r"September|October|November|December)\s+\d{4}\b")
        hits = []
        for p in doc_files():
            with open(p, encoding="utf-8") as fh:
                for m in rx.finditer(fh.read()):
                    hits.append((rel(p), m.group(0)))
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
