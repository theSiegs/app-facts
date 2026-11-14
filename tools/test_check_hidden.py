"""Tests for tools/check_hidden.py: the schema, ids, package names, the channel-or-title rule, patterns,
actions, the rule cap and no personal data. python -m unittest discover -s tools"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_hidden as ch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def doc(*rules):
    return {"format": ch.FORMAT, "rules": list(rules)}


def rule(id="example-promo", **kw):
    out = {"id": id, "pkg": "com.example.app", "titlePattern": "Weekly deals", "action": "hide",
           "why": "An example app's promotion; not news."}
    out.update(kw)
    return {k: v for k, v in out.items() if v is not ...}


class CheckTest(unittest.TestCase):
    def ok(self, data):
        return ch.check_hidden(data)

    def bad(self, data):
        with self.assertRaises(ch.Bad):
            ch.check_hidden(data)

    def test_the_repo_file_passes(self):
        rules = ch.load(ROOT)
        self.assertIsNotNone(rules)
        self.assertGreaterEqual(len(rules), 1)

    def test_good_rules(self):
        rules = self.ok(doc(rule(), rule("b", titlePattern=..., channel="promo_channel"),
                            rule("c.d_e-1", channel=None, titlePattern="* new messages", action="hide_and_clear"),
                            rule("d", action=..., why=...)))
        self.assertEqual(len(rules), 4)
        self.assertEqual(self.ok(doc()), [])

    def test_schema(self):
        self.bad({"rules": []})
        self.bad({"format": "glint.hidden/2", "rules": []})
        self.bad({"format": ch.FORMAT, "rules": {}})
        self.bad({**doc(), "extra": 1})
        self.bad(doc("a rule"))
        self.bad(doc(rule(note="x")))

    def test_ids(self):
        for bad in ["", "-a", "Upper", "a b", "a/b", "a" * 65, 5, None, "a\n"]:
            self.bad(doc(rule(bad)))
        self.ok(doc(rule("a" * 64)))
        self.bad(doc(rule("same"), rule("same")))

    def test_package(self):
        for bad in ["example", "1com.example", "com.example.", "com example.app", "com.example.app\n", None, 3,
                    "c." + "a" * 254]:
            self.bad(doc(rule(pkg=bad)))
        self.ok(doc(rule(pkg="com.Example_1.app2")))

    def test_channel(self):
        for bad in ["", "two words", "tab\there", "x" * 256, 7]:
            self.bad(doc(rule(channel=bad)))
        self.ok(doc(rule(channel="x" * 255)))

    def test_channel_or_title_required(self):
        self.bad(doc(rule(titlePattern=...)))
        self.bad(doc(rule(titlePattern=None, channel=None)))

    def test_title_pattern(self):
        for bad in ["", "   ", "*", "***", " ** ", "x" * 201, 9]:
            self.bad(doc(rule(titlePattern=bad)))
        self.ok(doc(rule(titlePattern=" " + "x" * 200 + " ")))
        self.ok(doc(rule(titlePattern="\\*")))
        self.ok(doc(rule(titlePattern="*Device pairing*")))

    def test_action(self):
        for bad in ["clear", "HIDE", "", None, 1]:
            self.bad(doc(rule(action=bad)))

    def test_cap(self):
        self.ok(doc(*[rule(f"r{n}") for n in range(ch.MAX_RULES)]))
        self.bad(doc(*[rule(f"r{n}") for n in range(ch.MAX_RULES + 1)]))

    def test_no_personal_data(self):
        for text in ["Write to a@b.co", "See https://x", "Booking.com", "Call 555 123 4567"]:
            self.bad(doc(rule(why=text)))
            self.bad(doc(rule(titlePattern=text)))
        self.bad(doc(rule(channel="a@b.co")))
        self.bad(doc(rule(why="two\nlines")))
        self.bad(doc(rule(why="x" * (ch.WHY_MAX + 1))))
        self.bad(doc(rule(why="")))

    def test_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(ch.load(tmp))
            with open(os.path.join(tmp, "hidden.json"), "w", encoding="utf-8") as f:
                f.write("{not json")
            with self.assertRaises(ch.Bad):
                ch.load(tmp)
            with open(os.path.join(tmp, "hidden.json"), "w", encoding="utf-8") as f:
                json.dump(doc(rule()), f)
            self.assertEqual(len(ch.load(tmp)), 1)


if __name__ == "__main__":
    unittest.main()
