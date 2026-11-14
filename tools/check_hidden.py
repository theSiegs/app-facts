#!/usr/bin/env python3
"""Checks Glint's starter list of notifications it hides (README.md, "Hidden notifications"); standard library only.

    python tools/check_hidden.py [--root .]

hidden.json (format glint.hidden/1, Glint's docs/contracts/hidden-notifications.md) must pass what Glint's
parser (Starters.parse) accepts, strictly: Glint skips an odd entry, the catalog refuses it, so every rule
published is one every phone uses.
  - schema: {"format": "glint.hidden/1", "rules": [...]}, each rule an object with only the known keys
  - id: [a-z0-9][a-z0-9._-]{0,63}, unique (a phone keeps its "turned off" choice by id)
  - pkg: an Android package name
  - channel: absent/null, or 1..255 characters with no white space
  - titlePattern: absent/null, or 1..200 characters once trimmed, not only stars
  - a channel or a titlePattern (never a whole app)
  - action: absent, "hide" or "hide_and_clear"
  - at most 500 rules
  - no personal data: no email address, link or phone number in any text, and why is one line
Also gives what is published (load()), used by tools/build_index.py.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_categories  # noqa: E402

FORMAT = "glint.hidden/1"
MAX_RULES = 500
MAX_PATTERN = 200
WHY_MAX = 300
ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
# check_categories.PACKAGE, matched whole (its $ would let a trailing newline through; Glint's wouldn't)
PACKAGE = re.compile(check_categories.PACKAGE.pattern.lstrip("^").rstrip("$"))
# Java's \s (ASCII white space), as Glint's Regex("""^[^\s]{1,255}$""") sees it
CHANNEL = re.compile(r"[^ \t\n\x0b\f\r]{1,255}")
ACTIONS = ("hide", "hide_and_clear")
RULE_KEYS = {"id", "pkg", "channel", "titlePattern", "action", "why"}
EMAIL, LINK, PHONE = check_categories.EMAIL, check_categories.LINK, check_categories.PHONE


class Bad(Exception):
    pass


def personal(where, key, text):
    if any(ord(ch) < 32 for ch in text):
        raise Bad(f"{where}: {key} has a control character")
    if EMAIL.search(text) or LINK.search(text) or PHONE.search(text):
        raise Bad(f"{where}: {key} looks like it holds an email address, link or phone number")


def check_rule(where, r, ids):
    if not isinstance(r, dict):
        raise Bad(f"{where}: a rule is an object")
    if set(r) - RULE_KEYS:
        raise Bad(f"{where}: unknown keys {sorted(set(r) - RULE_KEYS)}; a rule has only {sorted(RULE_KEYS)}")
    rid = r.get("id")
    if not isinstance(rid, str) or not ID.fullmatch(rid):
        raise Bad(f"{where}: id {rid!r} is not [a-z0-9][a-z0-9._-]{{0,63}}")
    if rid in ids:
        raise Bad(f"{where}: id {rid!r} is used twice")
    where = f"hidden.json {rid}"
    pkg = r.get("pkg")
    if not isinstance(pkg, str) or len(pkg) > 255 or not PACKAGE.fullmatch(pkg):
        raise Bad(f"{where}: pkg {pkg!r} is not an Android package name")
    channel = r.get("channel")
    if channel is not None:
        if not isinstance(channel, str) or not CHANNEL.fullmatch(channel):
            raise Bad(f"{where}: channel must be 1..255 characters with no white space, or null")
        personal(where, "channel", channel)
    pattern = r.get("titlePattern")
    if pattern is not None:
        if not isinstance(pattern, str):
            raise Bad(f"{where}: titlePattern must be a string or null")
        p = pattern.strip()
        if not p or len(p) > MAX_PATTERN:
            raise Bad(f"{where}: titlePattern must be 1..{MAX_PATTERN} characters")
        if all(ch == "*" for ch in p):
            raise Bad(f"{where}: titlePattern is only stars, which would hide every title")
        personal(where, "titlePattern", p)
    if channel is None and pattern is None:
        raise Bad(f"{where}: needs a channel or a titlePattern; a rule never hides a whole app")
    action = r.get("action", "hide")
    if action not in ACTIONS:
        raise Bad(f"{where}: action {action!r} is not one of {ACTIONS}")
    if "why" in r:
        why = r["why"]
        if not isinstance(why, str) or not why.strip() or len(why) > WHY_MAX or why != " ".join(why.split()):
            raise Bad(f"{where}: why must be one line of 1..{WHY_MAX} characters")
        personal(where, "why", why)
    return rid


def check_hidden(data):
    """The rules of a hidden.json document, checked."""
    if not isinstance(data, dict) or data.get("format") != FORMAT or not isinstance(data.get("rules"), list):
        raise Bad(f'hidden.json: must be {{"format": "{FORMAT}", "rules": [...]}}')
    if set(data) - {"format", "rules"}:
        raise Bad(f"hidden.json: unknown keys {sorted(set(data) - {'format', 'rules'})}")
    if len(data["rules"]) > MAX_RULES:
        raise Bad(f"hidden.json: {len(data['rules'])} rules, more than {MAX_RULES} (Glint reads only the first {MAX_RULES})")
    ids = set()
    for n, r in enumerate(data["rules"]):
        ids.add(check_rule(f"hidden.json rule {n + 1}", r, ids))
    return data["rules"]


def load(root):
    """The checked rules of the catalog at [root]; None when it has no hidden.json."""
    path = os.path.join(root, "hidden.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except ValueError as e:
            raise Bad(f"hidden.json: not JSON ({e})") from e
    return check_hidden(data)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args()
    try:
        rules = load(a.root)
    except Bad as e:
        print(f"check_hidden: {e}", file=sys.stderr)
        return 1
    if rules is None:
        print("hidden.json: none (Glint keeps its bundled starter list)")
    else:
        print(f"hidden.json: {len(rules)} rules, {sum(r.get('action') == 'hide_and_clear' for r in rules)} also cleared")
    return 0


if __name__ == "__main__":
    sys.exit(main())
