import importlib.util
import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rotate_news", ROOT / "rotate-news.py")
rot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rot)

TODAY = date(2026, 11, 14)


def art(id, d, title="t"):
    a = {"id": id, "title": title, "sources": ["s"]}
    if d is not None:
        a["date"] = d
    return a


def news(*arts):
    return {"schemaVersion": 1, "editorial": "O Corvo Investigador", "edition": "14/11/2026",
            "updatedAt": "2026-11-14T10:00:00-03:00", "tz": "America/Sao_Paulo",
            "articles": list(arts), "principles": ["p"]}


def ids(d):
    return [a["id"] for a in d["articles"]]


class RotateTests(unittest.TestCase):
    def test_old_articles_move_by_date(self):
        n, changed = rot.rotate(news(art("a14", "2026-11-14"), art("a13", "2026-11-13"),
                                     art("a12", "2026-11-12"), art("a10", "2026-11-10")), {}, TODAY)
        self.assertEqual(ids(n), ["a14", "a13"])
        self.assertEqual(ids(changed["noticias-2026-11-12.json"]), ["a12"])
        self.assertEqual(ids(changed["noticias-2026-11-10.json"]), ["a10"])
        new = changed["noticias-2026-11-12.json"]
        self.assertEqual(new["edition"], "12/11/2026")
        self.assertEqual(new["updatedAt"], "2026-11-14T10:00:00-03:00")
        self.assertNotIn("principles", new)
        self.assertEqual(n["principles"], ["p"])

    def test_moved_article_replaces_stale_copies(self):
        snap = news(art("y", "2026-11-11"), art("x", "2026-11-10", "velho"))
        del snap["principles"]
        n, changed = rot.rotate(news(art("x", "2026-11-10", "novo")), {"noticias-2026-11-11.json": snap}, TODAY)
        for f in ("noticias-2026-11-11.json", "noticias-2026-11-10.json"):
            xs = [a for a in changed[f]["articles"] if a["id"] == "x"]
            self.assertEqual([a["title"] for a in xs], ["novo"], f)
        self.assertEqual(ids(changed["noticias-2026-11-11.json"]), ["y", "x"])

    def test_bad_or_future_dates_stay(self):
        arts = [art("e", ""), art("b", "14/11/2026"), art("f", "2026-12-01"), art("n", None), art("z", "2026-13-40")]
        n, changed = rot.rotate(news(*arts), {}, TODAY)
        self.assertEqual(ids(n), ["e", "b", "f", "n", "z"])
        self.assertEqual(changed, {})

    def test_articles_without_string_id_stay(self):
        sem = {"date": "2026-11-10", "title": "sem id"}
        nulo1, nulo2 = art(None, "2026-11-10", "n1"), art(None, "2026-11-10", "n2")
        n, changed = rot.rotate(news(sem, nulo1, nulo2), {}, TODAY)
        self.assertEqual(n["articles"], [sem, nulo1, nulo2])
        self.assertEqual(changed, {})

    def test_no_article_lost(self):
        archive = {"noticias-2026-11-11.json": news(art("old", "2026-11-11"), art("m", "2026-11-09"))}
        before = news(art("a14", "2026-11-14"), art("m", "2026-11-09"), art("a12", "2026-11-12"))
        all_before = set(ids(before)) | set(ids(archive["noticias-2026-11-11.json"]))
        n, changed = rot.rotate(before, archive, TODAY)
        after = {**archive, **changed}
        all_after = set(ids(n)).union(*(ids(d) for d in after.values()))
        self.assertEqual(all_before, all_after)

    def test_second_run_is_noop(self):
        archive = {"noticias-2026-11-11.json": news(art("x", "2026-11-10", "velho"))}
        n, changed = rot.rotate(news(art("a14", "2026-11-14"), art("x", "2026-11-10", "novo")), archive, TODAY)
        n2, changed2 = rot.rotate(n, {**archive, **changed}, TODAY)
        self.assertEqual(changed2, {})
        self.assertEqual(n2, n)

    def test_main_writes_only_changed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "public/arquivo").mkdir(parents=True)
            untouched = root / "public/arquivo/noticias-2026-11-01.json"
            untouched.write_text(json.dumps(news(art("q", "2026-11-01"))), encoding="utf-8")
            os.utime(untouched, ns=(10**18, 10**18))
            (root / "public/noticias.json").write_text(
                json.dumps(news(art("a14", "2026-11-14"), art("a12", "2026-11-12"))), encoding="utf-8")
            self.assertEqual(rot.main(root, TODAY), 1)
            self.assertEqual(untouched.stat().st_mtime_ns, 10**18)
            text = (root / "public/noticias.json").read_text(encoding="utf-8")
            self.assertTrue(text.startswith('{\n  "schemaVersion"'))
            self.assertTrue(text.endswith("}\n"))
            self.assertTrue((root / "public/arquivo/noticias-2026-11-12.json").exists())
            self.assertEqual(rot.main(root, TODAY), 0)


if __name__ == "__main__":
    unittest.main()
