import tempfile
import unittest
from pathlib import Path

from page_assets import finish_pages


class PageAssetsTests(unittest.TestCase):
    def test_google_fonts_become_own_fonts_and_assets_get_a_content_version(self):
        with tempfile.TemporaryDirectory() as d:
            pub = Path(d)
            (pub / "raven-editorial.css").write_text("a{}")
            (pub / "raven-related.js").write_text("x()")
            page = pub / "noticias/a/index.html"
            page.parent.mkdir(parents=True)
            page.write_text('<head><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
                            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@800;900&display=swap">'
                            '<link rel="stylesheet" href="../../raven-editorial.css"></head><body><script defer src="../../raven-related.js?v=old"></script>'
                            '<script src="https://cdn.example/raven-x.js"></script></body>')
            finish_pages(pub, [page])
            out = page.read_text()
            self.assertNotIn("fonts.googleapis", out)
            self.assertIn("src:url(/fonts/barlow-condensed-900.woff2)", out)
            self.assertRegex(out, r'href="\.\./\.\./raven-editorial\.css\?v=[0-9a-f]{8}"')
            self.assertRegex(out, r'src="\.\./\.\./raven-related\.js\?v=[0-9a-f]{8}"')
            self.assertIn('src="https://cdn.example/raven-x.js"', out)
            once = out
            finish_pages(pub, [page])
            self.assertEqual(page.read_text(), once, "rodar de novo não muda nada")


if __name__ == "__main__":
    unittest.main()
