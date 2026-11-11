import tempfile
import unittest
from pathlib import Path

from column_photos import photo_figure


class ColumnPhotoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.public = Path(self.tmp.name)
        (self.public / "editorial" / "photos").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_essay_with_credited_photo_gets_figure_with_credit(self):
        (self.public / "editorial/photos/ensaio-teste.jpg").write_bytes(b"\xff\xd8\xff")
        credits = {"ensaio-teste": {"path": "editorial/photos/ensaio-teste.jpg", "artist": "Fulano/Agência Brasil",
                                    "license": "uso com crédito", "caption": "Plenário do Senado <foto de arquivo>"}}
        html = photo_figure("ensaio-teste", credits, self.public, "Título")
        self.assertIn('<figure class="rc-col-story-photo">', html)
        self.assertIn('src="editorial/photos/ensaio-teste.jpg"', html)
        self.assertIn("Foto: Fulano/Agência Brasil", html)
        self.assertIn("Plenário do Senado &lt;foto de arquivo&gt;", html)

    def test_no_credit_or_missing_file_or_bad_path_gives_nothing(self):
        self.assertEqual(photo_figure("sem-foto", {}, self.public, "T"), "")
        credits = {"x-ensaio": {"path": "editorial/photos/x-ensaio.jpg", "artist": "A", "license": "L"}}
        self.assertEqual(photo_figure("x-ensaio", credits, self.public, "T"), "")
        (self.public / "editorial/photos/y-ensaio.jpg").write_bytes(b"\xff\xd8\xff")
        bad = {"y-ensaio": {"path": "../y-ensaio.jpg", "artist": "A", "license": "L"}}
        self.assertEqual(photo_figure("y-ensaio", bad, self.public, "T"), "")

    def test_photo_without_artist_is_not_shown(self):
        (self.public / "editorial/photos/z-ensaio.jpg").write_bytes(b"\xff\xd8\xff")
        credits = {"z-ensaio": {"path": "editorial/photos/z-ensaio.jpg", "license": "L"}}
        self.assertEqual(photo_figure("z-ensaio", credits, self.public, "T"), "")

    def test_real_photo_gets_smaller_webp_copies_with_srcset_and_size(self):
        from PIL import Image
        Image.new("RGB", (2000, 1000), "red").save(self.public / "editorial/photos/grande.jpg")
        Image.new("RGB", (500, 250), "red").save(self.public / "editorial/photos/pequena.jpg")
        credits = {s: {"path": f"editorial/photos/{s}.jpg", "artist": "A"} for s in ("grande", "pequena")}
        html = photo_figure("grande", credits, self.public, "T")
        self.assertIn('src="editorial/photos/grande-1280.webp"', html)
        self.assertIn('srcset="editorial/photos/grande-320.webp 320w, editorial/photos/grande-640.webp 640w, editorial/photos/grande-1280.webp 1280w"', html)
        self.assertIn('width="1280" height="640"', html)
        with Image.open(self.public / "editorial/photos/grande-640.webp") as im:
            self.assertEqual(im.size, (640, 320))
        small = photo_figure("pequena", credits, self.public, "T")  # never upscaled
        self.assertIn('srcset="editorial/photos/pequena-320.webp 320w, editorial/photos/pequena-500.webp 500w"', small)
        self.assertFalse((self.public / "editorial/photos/pequena-640.webp").exists())


if __name__ == "__main__":
    unittest.main()
