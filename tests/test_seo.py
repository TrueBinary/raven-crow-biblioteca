import json
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from raven_seo import build, stamp_first_seen


class SeoBuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        pub = self.root / "public"
        (pub / "noticias" / "estudo-tributacao" ).mkdir(parents=True)
        (pub / "coluna" / "familia-e-justica").mkdir(parents=True)
        (pub / "editorial" / "photos").mkdir(parents=True)
        for file, url in [
            (self.root / "index.html", "https://ravencrow.cloud/"),
            (pub / "noticias.html", "https://ravencrow.cloud/noticias"),
            (pub / "coluna.html", "https://ravencrow.cloud/coluna"),
            (pub / "livros.html", "https://ravencrow.cloud/livros"),
            (pub / "sobre.html", "https://ravencrow.cloud/sobre"),
            (pub / "apoie.html", "https://ravencrow.cloud/apoie"),
            (pub / "noticias" / "estudo-tributacao" / "index.html",
             "https://ravencrow.cloud/noticias/estudo-tributacao/"),
            (pub / "coluna" / "familia-e-justica" / "index.html",
             "https://ravencrow.cloud/coluna/familia-e-justica/"),
        ]:
            file.write_text('<html><head><title>Raven Crow</title><link rel="canonical" href="' +
                            url + '"></head><body>Texto publicado</body></html>', encoding="utf-8")
        (pub / "noticias.json").write_text(json.dumps({"articles": [
            {"id": "estudo-tributacao", "date": "2026-11-05",
             "title": "Debate sobre tributos", "subtitle": "O que muda na economia?",
             "sources": [{"url": "https://example.org/primary", "name": "Fonte"}]},
            {"id": "rascunho-inexistente", "date": "2026-11-06",
             "title": "Rascunho", "subtitle": "Não publicado"}
        ]}), encoding="utf-8")
        (pub / "coluna-ensaios.json").write_text(json.dumps({"essays": [
            {"id": "familia-e-justica", "date": "2026-11-04",
             "title": "Família e justiça", "subtitle": "Ensaio sobre responsabilidade",
             "section": "Fé e família"}]}), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_first_seen_is_kept_once_stamped_and_rejects_other_days(self):
        feed = self.root / "public/editorial-feed.json"
        feed.write_text(json.dumps({"articles": [
            {"id": "antiga", "date": "2026-11-05", "firstSeen": "2026-11-05T09:10:00-03:00"}]}), encoding="utf-8")
        antiga = {"id": "antiga", "date": "2026-11-05"}
        nova = {"id": "nova", "date": "2026-11-06"}
        ontem = {"id": "ontem", "date": "2026-11-05"}
        sem_fuso = {"id": "sem-fuso", "date": "2026-11-06"}
        stamp_first_seen(feed, [(antiga, "2026-11-05T18:00:00-03:00"), (nova, "2026-11-06T08:00:00-03:00"),
                                (ontem, "2026-11-06T08:00:00-03:00"), (sem_fuso, "2026-11-06T08:00:00")])
        self.assertEqual(antiga["firstSeen"], "2026-11-05T09:10:00-03:00")  # hora gravada não anda
        self.assertEqual(nova["firstSeen"], "2026-11-06T08:00:00-03:00")
        self.assertNotIn("firstSeen", ontem)  # edição de outro dia não é publicação
        self.assertNotIn("firstSeen", sem_fuso)

    def test_article_already_in_feed_without_stamp_is_not_backfilled(self):
        # A matéria já publicada antes do firstSeen existir: a edição só tem a hora da última atualização.
        feed = self.root / "public/editorial-feed.json"
        feed.write_text(json.dumps({"articles": [{"id": "velha", "date": "2026-11-09"}]}), encoding="utf-8")
        velha = {"id": "velha", "date": "2026-11-09"}
        stamp_first_seen(feed, [(velha, "2026-11-09T17:05:06-03:00")])
        self.assertNotIn("firstSeen", velha)

    def test_news_is_newsarticle_with_first_seen_time(self):
        (self.root / "public/editorial-feed.json").write_text(json.dumps({"articles": [
            {"id": "estudo-tributacao", "date": "2026-11-05", "firstSeen": "2026-11-05T09:10:00-03:00"}]}),
            encoding="utf-8")
        build(self.root)
        news = (self.root / "public/noticias/estudo-tributacao/index.html").read_text(encoding="utf-8")
        self.assertIn('"@type": "NewsArticle"', news)
        self.assertIn('"datePublished": "2026-11-05T09:10:00-03:00"', news)
        self.assertIn('property="article:published_time" content="2026-11-05T09:10:00-03:00"', news)
        essay = (self.root / "public/coluna/familia-e-justica/index.html").read_text(encoding="utf-8")
        self.assertIn('"@type": "Article"', essay)

    def test_news_without_edition_time_keeps_plain_date_and_sitemap_dates(self):
        build(self.root)
        news = (self.root / "public/noticias/estudo-tributacao/index.html").read_text(encoding="utf-8")
        self.assertIn('"datePublished": "2026-11-05"', news)
        self.assertNotIn("T", re.search(r'"datePublished": "([^"]+)"', news).group(1))

    def test_news_sitemap_only_recent_published_articles(self):
        from datetime import date
        pub = self.root / "public"
        build(self.root, today=date(2026, 11, 7))
        tree = ET.parse(pub / "sitemap-news.xml").getroot()
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "n": "http://www.google.com/schemas/sitemap-news/0.9"}
        urls = [u.find("s:loc", ns).text for u in tree.findall("s:url", ns)]
        self.assertEqual(urls, ["https://ravencrow.cloud/noticias/estudo-tributacao/"])  # rascunho sem página fica fora
        self.assertEqual(tree.find(".//n:publication_date", ns).text, "2026-11-05")
        self.assertEqual(tree.find(".//n:name", ns).text, "Raven Crow")
        self.assertIn("Sitemap: https://ravencrow.cloud/sitemap-news.xml", (pub / "robots.txt").read_text(encoding="utf-8"))
        build(self.root, today=date(2026, 11, 9))  # 4 dias depois: sai do sitemap de notícias
        self.assertEqual(ET.parse(pub / "sitemap-news.xml").getroot().findall("s:url", ns), [])
        self.assertEqual((pub / "robots.txt").read_text(encoding="utf-8").count("sitemap-news.xml"), 1)

    def test_column_sitemap_tracks_published_editions_with_true_dates(self):
        pub = self.root / "public"
        data = json.loads((pub / "coluna-ensaios.json").read_text(encoding="utf-8"))
        data["essays"][0].update({
            "en": {"title": "Family and justice", "paragraphs": ["Published translation"]},
            "es": {"title": "Familia y justicia", "paragraphs": ["Traducción publicada"]},
        })
        (pub / "coluna-ensaios.json").write_text(json.dumps(data), encoding="utf-8")
        en_url = "https://ravencrow.cloud/en/column/familia-e-justica/"
        en_page = pub / "en" / "column" / "familia-e-justica" / "index.html"
        en_page.parent.mkdir(parents=True)
        en_page.write_text('<html><head><title>Essay</title><link rel="canonical" href="' +
                           en_url + '"></head><body>Published</body></html>', encoding="utf-8")
        es_page = pub / "es" / "columna" / "familia-e-justica" / "index.html"
        es_page.parent.mkdir(parents=True)
        es_page.write_text("<html><head><title>Essay</title></head><body>Missing canonical</body></html>",
                           encoding="utf-8")
        orphan_url = "https://ravencrow.cloud/en/column/orphan-draft/"
        orphan = pub / "en" / "column" / "orphan-draft" / "index.html"
        orphan.parent.mkdir(parents=True)
        orphan.write_text('<html><head><title>Draft</title><link rel="canonical" href="' +
                          orphan_url + '"></head><body>Draft</body></html>', encoding="utf-8")

        build(self.root)

        sitemap = pub / "sitemap-coluna.xml"
        self.assertTrue(sitemap.is_file(), "column sitemap was not generated")
        tree = ET.parse(sitemap).getroot()
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        entries = {
            item.find("s:loc", ns).text: item.findtext("s:lastmod", namespaces=ns)
            for item in tree.findall("s:url", ns)
        }
        self.assertEqual(entries, {
            "https://ravencrow.cloud/coluna": "2026-11-04",
            "https://ravencrow.cloud/coluna/familia-e-justica/": "2026-11-04",
            "https://ravencrow.cloud/en/column/familia-e-justica/": "2026-11-04",
        })

    def test_sitemap_only_has_rendered_canonical_pages_with_true_dates(self):
        build(self.root)
        tree = ET.parse(self.root / "public" / "sitemap.xml")
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        entries = {}
        for item in tree.findall("s:url", ns):
            entries[item.find("s:loc", ns).text] = item.findtext("s:lastmod", namespaces=ns)
        self.assertEqual(len(entries), 8)
        self.assertNotIn("https://ravencrow.cloud/noticias/rascunho-inexistente/", entries)
        self.assertEqual(entries["https://ravencrow.cloud/noticias/estudo-tributacao/"], "2026-11-05")
        self.assertEqual(entries["https://ravencrow.cloud/coluna/familia-e-justica/"], "2026-11-04")

    def test_structured_data_uses_article_dates_sources_and_site_identity(self):
        build(self.root)
        news = (self.root / "public/noticias/estudo-tributacao/index.html").read_text(encoding="utf-8")
        self.assertIn('"datePublished": "2026-11-05"', news)
        self.assertIn('"dateModified": "2026-11-05"', news)
        self.assertIn('"citation": ["https://example.org/primary"]', news)
        self.assertIn('"@type": "BreadcrumbList"', news)
        self.assertIn('property="og:locale" content="pt_BR"', news)
        essay = (self.root / "public/coluna/familia-e-justica/index.html").read_text(encoding="utf-8")
        self.assertIn('"@type": "Article"', essay)
        self.assertIn('"genre": "Opinião"', essay)
        self.assertIn('"datePublished": "2026-11-04"', essay)
        home = (self.root / "index.html").read_text(encoding="utf-8")
        self.assertIn('"@type": "Organization"', home)
        self.assertIn('"@type": "WebSite"', home)

    def test_idempotency_and_no_visual_markup_changes(self):
        build(self.root)
        paths = [self.root / "index.html",
                 self.root / "public/sitemap.xml",
                 self.root / "public/noticias/estudo-tributacao/index.html"]
        initial = [p.read_bytes() for p in paths]
        build(self.root)
        self.assertEqual(initial, [p.read_bytes() for p in paths])
        self.assertIn("<body>Texto publicado</body>", paths[-1].read_text(encoding="utf-8"))
        self.assertEqual(paths[-1].read_text(encoding="utf-8").count("raven-seo:start"), 1)


    def test_preexisting_unrelated_schema_is_not_removed_on_repeat(self):
        page = self.root / "public/noticias/estudo-tributacao/index.html"
        before = page.read_text(encoding="utf-8")
        legacy = ('<script type="application/ld+json">{"@type":"Article","headline":"Legado"}</script>'
                  '<script type="application/ld+json">{"@type":"FAQPage","mainEntity":[]}</script>')
        page.write_text(before.replace("</head>", legacy + "</head>"), encoding="utf-8")
        build(self.root)
        initial = page.read_bytes()
        build(self.root)
        later = page.read_text(encoding="utf-8")
        self.assertEqual(initial, page.read_bytes())
        self.assertEqual(later.count("FAQPage"), 1)
        self.assertEqual(later.count('"@type": "NewsArticle"'), 1)
        self.assertNotIn('"headline":"Legado"', later)


    def test_published_article_without_canonical_gets_safe_canonical(self):
        page = self.root / "public/noticias/estudo-tributacao/index.html"
        before = page.read_text(encoding="utf-8")
        expected = "https://ravencrow.cloud/noticias/estudo-tributacao/"
        page.write_text(before.replace('<link rel="canonical" href="' + expected + '">', ""),
                        encoding="utf-8")
        build(self.root)
        after = page.read_text(encoding="utf-8")
        self.assertIn('<link rel="canonical" href="' + expected + '">', after)
        self.assertIn('"@type": "NewsArticle"', after)
        self.assertIn(expected, (self.root / "public/sitemap.xml").read_text(encoding="utf-8"))


class BuildRavenWiringTests(unittest.TestCase):
    def test_first_seen_is_stamped_before_feed_is_rewritten(self):
        src = (Path(__file__).resolve().parents[1] / "build-raven.py").read_text(encoding="utf-8")
        stamp = src.index("stamp_first_seen(ROOT/'public/editorial-feed.json'")
        write = src.index("(ROOT/'public/editorial-feed.json').write_text(")
        self.assertLess(stamp, write)


if __name__ == "__main__":
    unittest.main()
