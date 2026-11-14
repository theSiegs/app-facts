"""Tests for tools/values.py: the values table's form, what the checkers take from it, and the add-only
rule. python -m unittest discover -s tools"""
import copy
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_catalog as ck  # noqa: E402
import check_categories as cc  # noqa: E402
import values  # noqa: E402


def write(root, data):
    os.makedirs(os.path.join(root, "catalog"), exist_ok=True)
    with open(os.path.join(root, values.PATH), "w", encoding="utf-8") as f:
        json.dump(data, f)
    return root


class TableTest(unittest.TestCase):
    def test_repo_table(self):
        t = values.TABLE
        self.assertEqual(t.categories, ("game", "video", "audio", "image", "social", "news", "maps", "productivity",
                                        "accessibility", "messaging"))
        self.assertEqual(t.details, ("youtube", "streaming", "education", "companion", "system", "browser"))
        self.assertEqual(t.loose_categories, ("accessibility", "messaging"))
        self.assertEqual(t.loose_details, ("education", "companion", "system"))
        self.assertEqual(t.detail_categories["browser"], (None,))
        self.assertEqual(t.label("browser"), "Web browsers")
        self.assertIsNone(t.label("unknown"))

    def test_checkers_read_it(self):
        self.assertEqual(cc.CATEGORIES, values.TABLE.categories)
        self.assertEqual(ck.DETAILS, values.TABLE.details)
        self.assertEqual(ck.DETAIL_CATEGORIES, values.TABLE.detail_categories)
        self.assertEqual(ck.LOOSE, values.TABLE.loose_details)
        self.assertEqual(ck.LOOSE_CATEGORIES, values.TABLE.loose_categories)

    def test_browser_detail_has_no_category(self):
        ck.check_detail("x", None, "browser")
        ck.check_detail("x", "unknown", "browser")
        with self.assertRaises(ck.Bad):
            ck.check_detail("x", "productivity", "browser")

    def test_bad_tables(self):
        good = values.TABLE.data
        values.check(copy.deepcopy(good))
        def broken(f):
            d = copy.deepcopy(good)
            f(d)
            return d
        for d in (
            broken(lambda d: d.update(format="glint.values/2")),
            broken(lambda d: d.update(extra=1)),
            broken(lambda d: d["categories"].update(unknown={"label": "Unknown", "pool": "other"})),
            broken(lambda d: d["categories"].update(Bad={"label": "Bad", "pool": "other"})),
            broken(lambda d: d["categories"]["game"].update(pool="fun")),
            broken(lambda d: d["categories"]["game"].pop("label")),
            broken(lambda d: d["categories"]["game"].update(label="x" * 31)),
            broken(lambda d: d["categories"]["game"].update(loose=False)),
            broken(lambda d: d["categories"]["game"].update(pool_names=[])),
            broken(lambda d: d["categories"]["game"].update(pool_names=["Games"])),
            broken(lambda d: d["details"]["browser"].update(parents=["web"])),
            broken(lambda d: d["details"]["browser"].update(parents=[])),
            broken(lambda d: d["details"]["browser"].update(outside_all=True)),
            broken(lambda d: d["details"].update(game={"label": "G", "parents": [None], "pool": "other"})),
        ):
            with self.assertRaises(values.Bad):
                values.check(d)


class AddOnlyTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.base = write(os.path.join(self.dir.name, "base"), values.TABLE.data)

    def tearDown(self):
        self.dir.cleanup()

    def head(self, f):
        d = copy.deepcopy(values.TABLE.data)
        f(d)
        return write(os.path.join(self.dir.name, "head"), d)

    def test_adding_passes(self):
        ck.values_only_added(self.base, self.head(lambda d: d["details"].update(
            reading={"label": "Reading", "parents": ["productivity", None], "pool": "other"})))
        ck.values_only_added(self.base, self.head(lambda d: d["categories"]["news"].update(label="News and magazines")))

    def test_removing_or_renaming_is_refused(self):
        for f in (lambda d: d["details"].pop("browser"),
                  lambda d: d["details"].update(web=d["details"].pop("browser")),
                  lambda d: d["categories"].pop("maps"),
                  lambda d: d["categories"]["messaging"].pop("loose")):
            with self.assertRaises(ck.Bad):
                ck.values_only_added(self.base, self.head(f))

    def test_no_base_table_is_fine(self):
        ck.values_only_added(os.path.join(self.dir.name, "nothing"), self.base)

    def test_table_gone_is_refused(self):
        with self.assertRaises(ck.Bad):
            ck.values_only_added(self.base, os.path.join(self.dir.name, "nothing"))


if __name__ == "__main__":
    unittest.main()
