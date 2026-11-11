import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("i18n_site", ROOT / "build-i18n-site.py")
site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site)


class TranslatorTests(unittest.TestCase):
    def t(self, words=None):
        return site.Translator("en", words or {}, {"nova-materia"}, {"ensaio-x"})

    def test_links_go_to_the_language_and_assets_to_the_root(self):
        t = self.t()
        self.assertEqual(t.link("/"), "/en/")
        self.assertEqual(t.link("/sobre"), "/en/about")
        self.assertEqual(t.link("/#biblioteca"), "/en/#biblioteca")
        self.assertEqual(t.link("noticias/nova-materia/"), "/en/news/nova-materia/")
        self.assertEqual(t.link("noticias/sem-traducao/"), "/noticias/sem-traducao/")
        self.assertEqual(t.link("coluna/ensaio-x/"), "/en/column/ensaio-x/")
        self.assertEqual(t.link("raven-logo.webp"), "/raven-logo.webp")
        self.assertEqual(t.link("https://pixgg.com/ravencrow"), "https://pixgg.com/ravencrow")

    def test_text_attributes_and_script_strings_are_translated_code_is_not(self):
        t = self.t({"Buscar": "Search", "Abrir menu": "Open menu", "Para pensar:": "Think about:", "Sobre nós": "About us"})
        out = t.page('<p> Buscar </p><button aria-label="Abrir menu" class="Buscar"></button><script>x.textContent=\'Para pensar: \';f(\'todos\')</script>'
                     '<script type="application/ld+json">{"a":"Buscar"}</script>')
        self.assertIn("<p> Search </p>", out)
        self.assertIn('aria-label="Open menu" class="Buscar"', out)
        self.assertIn("'Think about: '", out)
        self.assertIn("f('todos')", out)
        self.assertIn('{"a":"Buscar"}', out)
        self.assertNotIn("todos", t.missing)

    def test_untranslated_cards_and_links_are_dropped(self):
        html = ('<a class="rc-col-card " href="coluna/ensaio-x/">x</a><a class="rc-col-card " href="coluna/outro/">y</a>'
                '<li><a href="noticias/nova-materia/">a</a></li><li><a href="noticias/velha/">b</a></li>')
        out = site.drop_untranslated(html, {"nova-materia"}, {"ensaio-x"})
        self.assertIn("ensaio-x", out)
        self.assertNotIn("outro", out)
        self.assertIn("nova-materia", out)
        self.assertNotIn("velha", out)


class GeneratedPagesTests(unittest.TestCase):
    def test_every_page_text_has_a_translation(self):
        missing = site.build(write=False)
        self.assertEqual(missing, {"en": [], "es": []}, "rode: python build-i18n-site.py --extract e traduza i18n/missing.json em i18n/site.json")

    def test_translated_pages_are_self_contained(self):
        for lang, slugs in site.PAGE_SLUGS.items():
            for name in [""] + list(slugs):
                path = ROOT / "public" / lang / ((slugs[name] + ".html") if name else "index.html")
                page = path.read_text(encoding="utf-8")
                url = site.BASE + site.local_url(lang, name)
                self.assertIn(f'<html lang="{lang}">', page, path)
                self.assertIn(f'<link rel="canonical" href="{url}">', page, path)
                self.assertIn('hreflang="pt-BR"', page, path)
                self.assertIsNone(re.search(r'(?:src|href)="(?!/|https?:|#|mailto:|data:)[^"]+"', page), path)
                self.assertNotIn('href="/sobre"', page, path)


if __name__ == "__main__":
    unittest.main()
