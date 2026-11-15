#!/usr/bin/env python3
"""The catalog's one values table (README.md, "Values"): every category and detail, read from
catalog/values.json (glint.values/1). Standard library only. tools/check_categories.py,
tools/check_catalog.py and tools/build_index.py read it from here; the intake's classifier and relay
read the same file from a checkout of this repo.

    python tools/values.py [--root .] [--base <old values.json>]

{"format": "glint.values/1",
 "categories": {"<value>": {"label", "pool", "pool_names"?, "loose"?, "outside_all"?, "counted"?, "overrides_only"?}},
 "details":    {"<value>": {"label", "parents": ["<category>" | null, ...], "pool", "pool_names"?, "loose"?,
                            "counted"?, "overrides_only"?}}}

  label           a short display label (US English)
  pool            Hearth's default: "games", "social", "messaging" (its built-in pools) or "other"
  pool_names      names of a household's own pool that takes the value when there is one (else pool)
  loose           a value that can lift a limit: no store rule confirms it, only an override or a passing review
  outside_all     Hearth counts it outside All screen time by default
  counted         false: counted nowhere and never held or paused, so it has no pool (no pool, pool_names
                  or outside_all); left out, the value is counted in its pool
  overrides_only  strict: only an override (categories-overrides.json, catalog/overrides.json) or a device's
                  built-in list may set it, never the classifier, a store rule, a review or the relay; not
                  also loose (loose lets a review confirm it)
  parents         the categories a detail may sit under; null is no category

Add-only (README.md, "Values"): a value is never removed or renamed, never stops being loose or
overrides_only, and never becomes counted; the owner decides each addition. With --base it checks that
against an older table.
"""
import argparse
import json
import os
import re
import sys

FORMAT = "glint.values/1"
PATH = os.path.join("catalog", "values.json")
UNKNOWN = "unknown"
VALUE = re.compile(r"^[a-z][a-z_]{1,29}$")
POOLS = ("games", "social", "messaging", "other")
POOL_NAME = re.compile(r"^[a-z][a-z0-9_]{0,29}$")
LABEL_MAX = 30
CATEGORY_KEYS = {"label", "pool", "pool_names", "loose", "outside_all", "counted", "overrides_only"}
DETAIL_KEYS = {"label", "parents", "pool", "pool_names", "loose", "counted", "overrides_only"}


class Bad(Exception):
    pass


class Table:
    """A checked values table."""

    def __init__(self, data):
        self.data = data
        self.categories = tuple(data["categories"])
        self.details = tuple(data["details"])
        self.detail_categories = {d: tuple(v["parents"]) for d, v in data["details"].items()}
        self.loose_categories = tuple(c for c, v in data["categories"].items() if v.get("loose"))
        self.loose_details = tuple(d for d, v in data["details"].items() if v.get("loose"))
        # Values only an override (or a device's built-in list) may set: never the classifier, a store rule,
        # a review or the relay
        self.overrides_only_categories = tuple(c for c, v in data["categories"].items() if v.get("overrides_only"))
        self.overrides_only_details = tuple(d for d, v in data["details"].items() if v.get("overrides_only"))
        self.overrides_only = self.overrides_only_categories + self.overrides_only_details
        # Values counted nowhere (no pool)
        self.uncounted = tuple(n for kind in ("categories", "details") for n, v in data[kind].items()
                               if v.get("counted") is False)

    def label(self, value):
        v = self.data["categories"].get(value) or self.data["details"].get(value)
        return v["label"] if v else None


def _check_common(where, v, keys):
    if not isinstance(v, dict) or set(v) - keys or "label" not in v:
        raise Bad(f"{where}: an object with {sorted(keys)} (label required)")
    if "counted" in v and v["counted"] is not False:
        raise Bad(f"{where}: counted is false or left out")
    if "overrides_only" in v and v["overrides_only"] is not True:
        raise Bad(f"{where}: overrides_only is true or left out")
    if v.get("overrides_only") and "loose" in v:
        raise Bad(f"{where}: overrides_only and loose don't go together (loose lets a review confirm it)")
    if v.get("counted") is False:
        if set(v) & {"pool", "pool_names", "outside_all"}:
            raise Bad(f"{where}: a value counted nowhere has no pool, pool_names or outside_all")
    elif "pool" not in v:
        raise Bad(f"{where}: pool is required unless counted is false")
    label = v["label"]
    if not isinstance(label, str) or not label.strip() or len(label) > LABEL_MAX or label != " ".join(label.split()):
        raise Bad(f"{where}: label is one line of 1..{LABEL_MAX} characters")
    if "pool" in v and v["pool"] not in POOLS:
        raise Bad(f"{where}: pool {v['pool']!r} is not one of {POOLS}")
    names = v.get("pool_names", [])
    if not isinstance(names, list) or not names and "pool_names" in v or \
            not all(isinstance(n, str) and POOL_NAME.match(n) for n in names) or len(set(names)) != len(names):
        raise Bad(f"{where}: pool_names is a non-empty list of distinct lower-case names")
    for flag in ("loose", "outside_all"):
        if flag in v and v[flag] is not True:
            raise Bad(f"{where}: {flag} is true or left out")


def check(data):
    """A Table from a values.json document, checked."""
    if not isinstance(data, dict) or data.get("format") != FORMAT or set(data) != {"format", "categories", "details"}:
        raise Bad(f'values.json: must be {{"format": "{FORMAT}", "categories": {{...}}, "details": {{...}}}}')
    cats, details = data["categories"], data["details"]
    if not isinstance(cats, dict) or not cats or not isinstance(details, dict):
        raise Bad("values.json: categories (not empty) and details are objects")
    for name in list(cats) + list(details):
        if not VALUE.match(name) or name == UNKNOWN:
            raise Bad(f"values.json: {name!r} is not a value name ([a-z][a-z_]{{1,29}}, not unknown)")
    both = set(cats) & set(details)
    if both:
        raise Bad(f"values.json: {sorted(both)} are both a category and a detail")
    for c, v in cats.items():
        _check_common(f"values.json category {c}", v, CATEGORY_KEYS)
    for d, v in details.items():
        where = f"values.json detail {d}"
        _check_common(where, v, DETAIL_KEYS)
        if "outside_all" in v:
            raise Bad(f"{where}: outside_all is for categories")
        parents = v.get("parents")
        if not isinstance(parents, list) or not parents or len(set(map(str, parents))) != len(parents) or \
                any(p is not None and p not in cats for p in parents):
            raise Bad(f"{where}: parents is a non-empty list of distinct categories or null")
    return Table(data)


def load(root):
    """The Table at [root] (a checkout of this repo), or None when it has no values.json."""
    path = os.path.join(root, PATH)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        try:
            return check(json.load(f))
        except ValueError as e:
            raise Bad(f"values.json: not JSON ({e})") from e


def removed(old, new):
    """What [new] drops from [old], which the add-only rule refuses: a category or detail gone (a rename
    is one gone and one added), or a value that stops being loose or overrides_only, or becomes counted.
    Empty when it only adds."""
    out = []
    for kind in ("categories", "details"):
        for name, v in old.data[kind].items():
            n = new.data[kind].get(name)
            if n is None:
                out.append(f"{kind[:-1] if kind == 'details' else 'category'} {name} removed or renamed")
            elif v.get("loose") and not n.get("loose"):
                out.append(f"{name} stops being loose")
            elif v.get("overrides_only") and not n.get("overrides_only"):
                out.append(f"{name} stops being overrides_only")
            elif v.get("counted") is False and n.get("counted") is not False:
                out.append(f"{name} becomes counted")
    return out


def check_base(old, new):
    gone = removed(old, new)
    if gone:
        raise Bad("values.json is add-only (README.md, \"Values\"): " + "; ".join(gone))


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE = load(ROOT)
if TABLE is None:
    raise Bad(f"{os.path.join(ROOT, PATH)} is missing")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--base", help="the values.json being replaced (a pull request's base): add-only")
    a = ap.parse_args()
    try:
        table = load(a.root)
        if table is None:
            raise Bad(f"no {PATH} under {a.root}")
        if a.base and os.path.isfile(a.base):
            with open(a.base, encoding="utf-8") as f:
                check_base(check(json.load(f)), table)
    except (Bad, ValueError) as e:
        print(f"values: {e}", file=sys.stderr)
        return 1
    print(f"values: {len(table.categories)} categories, {len(table.details)} details, "
          f"{len(table.overrides_only)} only by override")
    return 0


if __name__ == "__main__":
    sys.exit(main())
