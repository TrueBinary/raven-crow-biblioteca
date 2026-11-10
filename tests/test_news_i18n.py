import tempfile
import unittest
from pathlib import Path

from news_i18n import block, langs_of, render_article, render_index


class NewsI18nTests(unittest.TestCase):
    def test_incomplete_block_gets_no_page(self):
        self.assertIsNone(block({"en": {"title": "T", "facts": ""}}, "en"))
        self.assertEqual(langs_of({"es": {"title": "T", "facts": "F", "analysis": "A", "counterpoint": "C"}}), ["es"])

    def test_pages_have_canonical_hreflang_and_translated_caption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "public/editorial/photos").mkdir(parents=True)
            (root / "public/editorial/photos/nova-2026.jpg").write_bytes(b"\xff\xd8\xff")
            body = {"subtitle": "Sub", "facts": "F", "analysis": "A", "counterpoint": "C"}
            a = {"id": "nova-2026", "date": "2026-11-08", "sources": [{"name": "S", "url": "https://x.org"}],
                 "en": {**body, "title": "Big news", "photo_captions": {"1": "English caption"}},
                 "es": {**body, "title": "Gran noticia"}}
            credits = {"nova-2026": {"path": "editorial/photos/nova-2026.jpg", "artist": "X/Agência Brasil", "caption": "Legenda"}}
            url = render_article(root, a, "en", "", credits, "", "https://b", lambda t: t)
            render_article(root, a, "es", "", credits, "", "https://b", lambda t: t)
            en = (root / "public/en/noticias/nova-2026/index.html").read_text(encoding="utf-8")
            es = (root / "public/es/noticias/nova-2026/index.html").read_text(encoding="utf-8")
            self.assertEqual(url, "https://b/en/noticias/nova-2026/")
            self.assertIn('<link rel="canonical" href="https://b/en/noticias/nova-2026/">', en)
            self.assertIn('hreflang="es" href="https://b/es/noticias/nova-2026/"', en)
            self.assertIn('hreflang="pt-BR" href="https://b/noticias/nova-2026/"', es)
            self.assertIn("English caption", en)
            self.assertNotIn("Legenda", en)
            self.assertIn("8 de noviembre de 2026", es)
            self.assertIn('"image": "https://b/editorial/photos/nova-2026.jpg"', en)
            self.assertIn('<meta property="og:image" content="https://b/editorial/photos/nova-2026.jpg">', es)
            self.assertIn('src="../../../editorial/photos/nova-2026.jpg"', es)
            self.assertIn('"@type": "NewsArticle"', en)
            self.assertRegex(es, r'<footer class="rc-foot"><span>[^<]*<time datetime="2026-11-08">8 de noviembre de 2026</time></span>')
            render_index(root, "es", [a], "", "https://b")
            self.assertIn("Gran noticia", (root / "public/es/index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
