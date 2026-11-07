"""Shared helpers for HISS-Assess: paths, file reading and writing, list parsing and small statistics.

Standard library only. Everything here is pure or touches only the paths it is given,
so the other modules can be imported and tested without side effects.
"""
import csv
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(ROOT, "config")
CATALOGUE_DIR = os.path.join(ROOT, "catalogue")
INPUTS_DIR = os.path.join(ROOT, "inputs")
OUT_DIR = os.path.join(ROOT, "outputs")
DOCS_DIR = os.path.join(ROOT, "docs")

AUTHOR = "Raghunath Thiyagarajan"
MAX_MATURITY = 4

# Order used wherever domains are listed: six foundation domains then ten hotel domains.
DOMAIN_ORDER = ["F1", "F2", "F3", "F4", "F5", "F6",
                "H01", "H02", "H03", "H04", "H05", "H06", "H07", "H08", "H09", "H10"]


def resolve_path(path, default_base=ROOT):
    """Return an absolute path. A relative path is tried against the working folder first and then the toolkit folder."""
    if os.path.isabs(path):
        return path
    here = os.path.abspath(path)
    if os.path.exists(here):
        return here
    return os.path.join(default_base, path)


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def read_csv_header(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        try:
            return next(reader)
        except StopIteration:
            return []


def write_csv(path, rows, fieldnames):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def read_json(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def write_json(path, obj):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=True)
        fh.write("\n")


def write_text(path, text):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def split_list(value):
    """Split a semicolon list cell into clean items."""
    if value is None:
        return []
    return [x.strip() for x in str(value).split(";") if x.strip()]


def to_int(value, default=None):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def pct(value, digits=1):
    """Round a fraction between 0 and 1 to a percentage."""
    if value is None:
        return None
    return round(100.0 * value, digits)


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def domain_sort_key(code):
    try:
        return (DOMAIN_ORDER.index(code), code)
    except ValueError:
        return (len(DOMAIN_ORDER), code)


def average_ranks(values):
    """Ranks with ties given the average rank (1 is the smallest value)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(a, b):
    """Spearman rank correlation of two equal length lists. Returns None when it is undefined."""
    if len(a) != len(b) or len(a) < 2:
        return None
    ra, rb = average_ranks(a), average_ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = math.sqrt(sum((x - ma) ** 2 for x in ra))
    db = math.sqrt(sum((y - mb) ** 2 for y in rb))
    if da == 0 or db == 0:
        return None
    return num / (da * db)
