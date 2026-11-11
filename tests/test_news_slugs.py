import json
import tempfile
import unittest
from pathlib import Path

from news_i18n import assign_slugs, local_slug, slugify


def art(id_, en_title, es_title=None, date="2026-11-12"):
    a = {"id": id_, "date": date, "title": "T", "en": {"title": en_title, "facts": "f", "analysis": "a", "counterpoint": "c"}}
    if es_title:
        a["es"] = {"title": es_title, "facts": "f", "analysis": "a", "counterpoint": "c"}
    return a


class SlugTests(unittest.TestCase):
    def test_slugify_drops_accents_and_punctuation(self):
        self.assertEqual(slugify("Lula luta contra Alcolumbre: ¿qué pasó?"), "lula-luta-contra-alcolumbre-que-paso")
        self.assertLessEqual(len(slugify("palavra " * 40)), 80)

    def test_new_article_gets_title_slug_in_each_language_and_it_never_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / "public").mkdir()
            a = art("lula-luta-contra-alcolumbre-2026-11-12", "Lula fights Alcolumbre", "Lula pelea contra Alcolumbre")
            assign_slugs(root, [a])
            self.assertEqual(local_slug(a, "en"), "lula-fights-alcolumbre-2026-11-12")
            self.assertEqual(local_slug(a, "es"), "lula-pelea-contra-alcolumbre-2026-11-12")
            b = art(a["id"], "Lula takes on Alcolumbre")  # título revisado depois de publicado
            assign_slugs(root, [b])
            self.assertEqual(local_slug(b, "en"), "lula-fights-alcolumbre-2026-11-12")
            self.assertEqual(json.loads((root / "public/news-slugs.json").read_text())[a["id"]]["en"], "lula-fights-alcolumbre-2026-11-12")

    def test_already_published_page_keeps_its_url_and_clashes_get_a_suffix(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "public/en/news/velha-2026-11-01").mkdir(parents=True)
            (root / "public/en/news/velha-2026-11-01/index.html").write_text("x")
            old, n1, n2 = art("velha-2026-11-01", "Old story"), art("x-2026-11-12", "Same title"), art("y-2026-11-12", "Same title")
            assign_slugs(root, [old, n1, n2])
            self.assertEqual(local_slug(old, "en"), "velha-2026-11-01")
            self.assertEqual({local_slug(n1, "en"), local_slug(n2, "en")}, {"same-title-2026-11-12", "same-title-2026-11-12-2"})

    def test_page_link_and_hreflang_use_the_language_slug(self):
        from news_i18n import render_article, render_index
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / "public").mkdir()
            a = art("lula-luta-contra-alcolumbre-2026-11-12", "Lula fights Alcolumbre", "Lula pelea contra Alcolumbre")
            assign_slugs(root, [a])
            url = render_article(root, a, "en", "", {}, "", "https://x", lambda t: t)
            self.assertEqual(url, "https://x/en/news/lula-fights-alcolumbre-2026-11-12/")
            page = (root / "public/en/news/lula-fights-alcolumbre-2026-11-12/index.html").read_text(encoding="utf-8")
            self.assertIn('hreflang="es" href="https://x/es/noticias/lula-pelea-contra-alcolumbre-2026-11-12/"', page)
            self.assertIn('href="../../../noticias/lula-luta-contra-alcolumbre-2026-11-12/" hreflang="pt-BR"', page)
            render_index(root, "es", [a], "", "https://x")
            self.assertIn('href="noticias/lula-pelea-contra-alcolumbre-2026-11-12/"', (root / "public/es/index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
