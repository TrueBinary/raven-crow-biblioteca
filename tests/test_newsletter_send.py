import json
import tempfile
import unittest
from pathlib import Path

import newsletter_send as ns


def _root(articles, essays, archive=None):
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    (root / "public/arquivo").mkdir(parents=True)
    (root / "public/noticias.json").write_text(json.dumps({"articles": articles}), encoding="utf-8")
    (root / "public/coluna-ensaios.json").write_text(json.dumps({"essays": essays}), encoding="utf-8")
    for day, arts in (archive or {}).items():
        (root / f"public/arquivo/noticias-{day}.json").write_text(json.dumps({"articles": arts}), encoding="utf-8")
    return tmp, root


class DigestTests(unittest.TestCase):
    def test_digest_lists_only_that_day_with_links_and_dedupes_archive(self):
        a1 = {"id": "a-1", "date": "2026-11-09", "title": "Título [um]", "subtitle": "Sub um", "category": "BRASIL"}
        a2 = {"id": "a-2", "date": "2026-11-10", "title": "Hoje", "subtitle": "x"}
        tmp, root = _root([a1, a2], [], {"2026-11-09": [a1, {"id": "a-3", "date": "2026-11-09", "title": "Três", "subtitle": "s3"}]})
        with tmp:
            mail = ns.digest(root, "2026-11-09")
        self.assertEqual(mail["slug"], "resumo-2026-11-09")
        self.assertIn("9 de novembro", mail["subject"])
        self.assertIn("(https://ravencrow.cloud/noticias/a-1/)", mail["body"])
        self.assertIn("(https://ravencrow.cloud/noticias/a-3/)", mail["body"])
        self.assertNotIn("a-2", mail["body"])
        self.assertEqual(mail["body"].count("noticias/a-1/"), 1)
        self.assertIn("Título \\[um\\]", mail["body"])
        self.assertTrue(mail["body"].rstrip().endswith("(https://www.youtube.com/channel/UC7QOwGdezKSy8NiaIalE9-w)."))
        self.assertIn("(https://www.instagram.com/ravencrowcc/)", mail["body"])

    def test_no_news_means_no_digest(self):
        tmp, root = _root([], [])
        with tmp:
            self.assertIsNone(ns.digest(root, "2026-11-09"))


class ColumnTests(unittest.TestCase):
    def test_only_todays_essays_with_full_text_and_link(self):
        e1 = {"id": "ensaio-hoje", "date": "2026-11-10", "title": "TÍTULO", "subtitle": "Sub", "paragraphs": ["P1", "P2"]}
        e2 = {"id": "ensaio-ontem", "date": "2026-11-09", "title": "Velho", "subtitle": "", "paragraphs": ["x"]}
        tmp, root = _root([], [e1, e2])
        with tmp:
            mails = ns.columns(root, "2026-11-10")
        self.assertEqual([m["slug"] for m in mails], ["coluna-ensaio-hoje"])
        self.assertIn("P1\n\nP2", mails[0]["body"])
        self.assertIn("(https://ravencrow.cloud/coluna/ensaio-hoje/)", mails[0]["body"])

    def test_slug_is_capped_and_safe(self):
        e = {"id": "x" * 120, "date": "2026-11-10", "title": "T", "subtitle": "", "paragraphs": ["p"]}
        tmp, root = _root([], [e])
        with tmp:
            slug = ns.columns(root, "2026-11-10")[0]["slug"]
        self.assertLessEqual(len(slug), 100)
        self.assertRegex(slug, r"^[a-zA-Z0-9_-]+$")


class SendTests(unittest.TestCase):
    def test_skips_slugs_already_on_buttondown(self):
        calls = []

        def api(method, path, body=None):
            calls.append((method, path, body))
            if method == "GET":
                return {"results": [{"slug": "resumo-2026-11-09"}], "next": None}
            return {"id": "em_1"}

        sent = ns.send([{"slug": "resumo-2026-11-09", "subject": "s", "body": "b"},
                        {"slug": "coluna-novo", "subject": "s2", "body": "b2"}], api)
        self.assertEqual(sent, ["coluna-novo"])
        posts = [c for c in calls if c[0] == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0][2]["status"], "about_to_send")
        self.assertEqual(posts[0][2]["slug"], "coluna-novo")


if __name__ == "__main__":
    unittest.main()
