"""Static SEO regression checks for the deployed HTML artifact tree."""
import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
BASE = "https://ravencrow.cloud"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class PublishedSeoTests(unittest.TestCase):
    def test_every_sitemap_url_has_canonical_generated_html(self):
        tree = ET.parse(PUBLIC / "sitemap.xml")
        urls = []
        for entry in tree.findall("s:url", NS):
            url = entry.findtext("s:loc", namespaces=NS)
            urls.append(url)
            self.assertTrue(url.startswith(BASE + "/"), url)
            path = urlparse(url).path
            page = ROOT / "index.html" if path == "/" else (
                PUBLIC / path.lstrip("/") / "index.html" if path.endswith("/")
                else PUBLIC / path.lstrip("/")
            )
            self.assertTrue(page.is_file(), url)
            html = page.read_text(encoding="utf-8")
            self.assertIn('<link rel="canonical" href="' + url + '">', html)
            self.assertIn('property="og:site_name" content="Raven Crow"', html)
            if "/noticias/" in path or "/coluna/" in path:
                scripts = re.findall(
                    r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
                graphs = [json.loads(s) for s in scripts]
                articles = [x for g in graphs for x in g.get("@graph", [])
                            if x.get("@type") in ("Article", "NewsArticle")]
                self.assertEqual(len(articles), 1, url)
                self.assertEqual(articles[0]["mainEntityOfPage"]["@id"], url)
                self.assertTrue(articles[0]["datePublished"], url)
        self.assertEqual(len(urls), len(set(urls)))
        self.assertGreaterEqual(len(urls), 15)

    def test_robots_declares_sitemap_without_blocking_google(self):
        robots = (PUBLIC / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("Sitemap: " + BASE + "/sitemap.xml", robots)
        self.assertNotIn("Disallow: /", robots)

    def test_home_presents_news_analysis_not_only_library(self):
        head = (ROOT / "index.html").read_text(encoding="utf-8").split("</head>")[0]
        title = re.search(r"<title>([^<]*)</title>", head).group(1)
        desc = re.search(r'<meta name="description" content="([^"]*)"', head).group(1)
        self.assertIn("análise", title.lower())
        self.assertFalse(title.startswith("Biblioteca"))
        self.assertIn("política", desc)
        self.assertLessEqual(len(desc), 155)


if __name__ == "__main__":
    unittest.main()
