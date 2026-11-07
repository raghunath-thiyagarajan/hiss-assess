"""Decide which controls and which legal obligations apply to a property.

Control rule (design section on profiles and levels):
  Baseline controls apply to every profile.
  Enhanced controls apply to the profiles listed on the control (normally M and G).
  An Enhanced control that does not list the profile still applies when one of its triggers is active,
  because a trigger makes it mandatory for a small property.

Obligation rule:
  The obligation jurisdiction tag must match a configured jurisdiction. Tags match when they are equal
  or when one is the parent of the other (AE covers AE-DXB, US covers US-NY).
  When the hotel_trigger text names a trigger code such as T5 that trigger must be active.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TRIGGER_RX = re.compile(r"\bT[1-5]\b")
OWNER_FIELD = {"owned": "owner_owned", "managed": "owner_managed", "franchised": "owner_franchised"}

APPLICABILITY_FIELDS = ["control_id", "domain", "title", "level", "profiles", "triggers", "applicable", "reason",
                        "active_triggers", "accountable"]


def accountable_party(control, operating_model):
    """Who is accountable for a control under the operating model: group, property, vendor or franchisee."""
    return control.get(OWNER_FIELD.get(operating_model, "owner_owned"), "")


def control_applies(control, profile, active_triggers):
    """Return (applies, reason, matched_triggers) for one control."""
    level = control.get("level")
    listed = control.get("profile_list") or [p for p in str(control.get("profiles", "")).split(";") if p]
    trig = control.get("trigger_list") or [t for t in str(control.get("triggers", "")).split(";") if t]
    matched = [t for t in trig if t in active_triggers]
    if level == "Baseline":
        return True, "Baseline applies to every profile", matched
    if profile in listed:
        return True, "Enhanced control listed for profile %s" % profile, matched
    if matched:
        return True, "Enhanced control made mandatory by trigger %s" % " and ".join(matched), matched
    if trig:
        return False, "Enhanced control not listed for profile %s and no trigger active (%s)" % (profile, "/".join(trig)), []
    return False, "Enhanced control not listed for profile %s and has no trigger" % profile, []


def filter_controls(controls, cfg):
    """Applicability row for every control, in catalogue order."""
    active = set(cfg["triggers"])
    rows = []
    for c in controls:
        ok, reason, matched = control_applies(c, cfg["profile"], active)
        rows.append({
            "control_id": c["control_id"], "domain": c["domain"], "title": c["title"], "level": c["level"],
            "profiles": c["profiles"], "triggers": c["triggers"],
            "applicable": "yes" if ok else "no", "reason": reason,
            "active_triggers": ";".join(matched),
            "accountable": accountable_party(c, cfg["operating_model"]),
        })
    return rows


def applicable_ids(rows):
    return [r["control_id"] for r in rows if r["applicable"] == "yes"]


def jurisdiction_matches(obligation_tag, configured_tag):
    """True when the tags are equal or one is the parent of the other."""
    a, b = obligation_tag.strip().upper(), configured_tag.strip().upper()
    return a == b or a.startswith(b + "-") or b.startswith(a + "-")


def obligation_scope(obligation, cfg):
    """Return (in_scope, basis, reason). basis is the label given to the matching configured jurisdiction."""
    tag = obligation.get("jurisdiction", "")
    basis = None
    for conf, label in cfg["jurisdictions"].items():
        if jurisdiction_matches(tag, conf):
            basis = label
            break
    if basis is None:
        return False, "", "jurisdiction %s is not configured" % tag
    needs = TRIGGER_RX.findall(obligation.get("hotel_trigger", "") or "")
    missing = [t for t in needs if t not in cfg["triggers"]]
    if missing:
        return False, basis, "trigger %s is not active" % " and ".join(missing)
    return True, basis, "in scope"
