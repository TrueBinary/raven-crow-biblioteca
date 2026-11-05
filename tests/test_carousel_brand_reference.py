"""Tests for the fixed Mercosul/EFTA image composition."""
import importlib.util
import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
module_spec = importlib.util.spec_from_file_location("raven_brand_renderer", ROOT / "carousel-brand-render.py")
renderer = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(renderer)


class BrandReferenceTests(unittest.TestCase):
    def test_sentence_beats_do_not_split_words_arbitrarily(self):
        source = "Menos tarifas de importação. Mais acesso a tecnologias. Novas oportunidades de comércio."
        self.assertEqual(renderer.editorial_beats(source), [
            "Menos tarifas de importação.",
            "Mais acesso a tecnologias.",
            "Novas oportunidades de comércio.",
        ])

    def test_interior_has_explicit_three_beats_and_brand_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            logo = Path(directory) / "logo-original-test.png"
            Image.new("RGBA", (90, 90), (227, 45, 59, 255)).save(logo)
            slides = [
                {"section": "ECONOMIA / COMÉRCIO", "title": "BRASIL E NORUEGA ABREM TARIFAS",
                 "body": "Acordo comercial e seus efeitos."},
                {"title": "O QUE MUDA?", "points": [
                    {"icon": "package", "text": "Menos tarifas sobre parte das importações."},
                    {"icon": "factory", "text": "Mais acesso a produtos e tecnologias."},
                    {"icon": "handshake", "text": "Novas oportunidades para negociar."},
                ]},
                {"title": "QUAL É O CONTEXTO?", "body": "O acordo tem etapas. O prazo depende de cada item. A implementação deve ser acompanhada."},
                {"title": "QUEM GANHA?", "body": "Nem todos os setores ganham igualmente. Há custos de adaptação. Resultados exigem avaliação."},
                {"title": "E O BRASIL, GANHA?", "body": "O resultado depende da capacidade de competir.",
                 "cta1": "LEIA A ANÁLISE COMPLETA", "cta2": "NA COLUNA DO CORVO"},
            ]
            unique_hashes = set()
            for number, slide in enumerate(slides, 1):
                im = renderer.render(slide, number, 5, str(logo), "05 NOV 2026")
                self.assertEqual(im.size, (1080, 1350))
                self.assertEqual(im.getpixel((5, 675)), (228, 46, 59))
                dest = Path(directory) / f"slide{number}.png"
                im.save(dest)
                unique_hashes.add(hashlib.sha256(dest.read_bytes()).hexdigest())
            self.assertEqual(len(unique_hashes), 5)

    def test_one_line_heading_highlights_only_the_last_word(self):
        from PIL import ImageDraw
        image=Image.new("RGB",(1080,1350),renderer.DARK)
        d=ImageDraw.Draw(image)
        renderer.title(d,"O QUE MUDA?",262,390,initial=120)
        colors=[image.getpixel((x,y)) for x in range(50,990,3) for y in range(262,420,3)]
        self.assertIn((228,46,59),colors)
        self.assertIn((246,244,240),colors)

    def test_missing_original_logo_fails_closed(self):
        with self.assertRaises((FileNotFoundError, OSError)):
            renderer.render({"title": "Teste", "body": "Contexto"}, 1, 5,
                            "arquivo-logo-inexistente.png", "05 NOV 2026")


if __name__ == "__main__":
    unittest.main()
