import tempfile
import unittest
from pathlib import Path

from news_photos import news_figures


def credit(key, placement=None):
    c = {"path": f"editorial/photos/{key}.jpg", "artist": "Fulano/Agência Brasil", "license": "uso com crédito", "caption": f"legenda {key}"}
    if placement:
        c["placement"] = placement
    return c


class NewsPhotoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.public = Path(self.tmp.name)
        (self.public / "editorial" / "photos").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, key):
        (self.public / f"editorial/photos/{key}.jpg").write_bytes(b"\xff\xd8\xff")

    def test_main_photo_goes_on_top_and_extras_in_their_sections(self):
        for k in ("nova-2026", "nova-2026--2", "nova-2026--3"):
            self.put(k)
        credits = {"nova-2026": credit("nova-2026"), "nova-2026--2": credit("nova-2026--2", "fatos"),
                   "nova-2026--3": credit("nova-2026--3", "contraponto")}
        f = news_figures("nova-2026", credits, self.public, "Título")
        self.assertIn('src="editorial/photos/nova-2026.jpg"', f["top"])
        self.assertIn('src="editorial/photos/nova-2026--2.jpg"', f["fatos"])
        self.assertEqual(f["analise"], "")
        self.assertIn('src="editorial/photos/nova-2026--3.jpg"', f["contraponto"])
        self.assertIn("Foto: Fulano/Agência Brasil", f["top"])
        self.assertIn(".rc-col-story-photo", f["style"])

    def test_extra_without_valid_placement_goes_after_analysis(self):
        self.put("nova-2026--2")
        f = news_figures("nova-2026", {"nova-2026--2": credit("nova-2026--2", "rodape")}, self.public, "T")
        self.assertIn("nova-2026--2.jpg", f["analise"])
        self.assertEqual(f["top"], "")

    def test_no_photos_means_no_markup_and_no_style(self):
        f = news_figures("nova-2026", {}, self.public, "T")
        self.assertEqual(set(f.values()), {""})

    def test_images_resolve_from_article_folder(self):
        self.put("nova-2026")
        f = news_figures("nova-2026", {"nova-2026": credit("nova-2026")}, self.public, "T", prefix="../../")
        self.assertIn('src="../../editorial/photos/nova-2026.jpg"', f["top"])


if __name__ == "__main__":
    unittest.main()
