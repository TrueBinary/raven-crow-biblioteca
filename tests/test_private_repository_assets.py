"""Regression: public site assets must not depend on private GitHub raw URLs."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "public"
URL = "https://ravencrow.cloud/santiago-pena-original.jpg"
SLUG = "santiago-pena-preso-apos-impeachment-2026"


class PrivateRepositoryAssetsTest(unittest.TestCase):
    def test_santiago_image_is_delivered_as_site_asset(self):
        photo = ROOT / "santiago-pena-original.jpg"
        self.assertTrue(photo.is_file(), "Santiago Pena image missing from public site")
        self.assertTrue(photo.read_bytes().startswith(b"\xff\xd8\xff"), "Invalid JPEG asset")

    def test_article_feeds_use_own_host(self):
        for name in ("noticias.json", "editorial-feed.json"):
            with self.subTest(name=name):
                data = json.loads((ROOT / name).read_text(encoding="utf-8"))
                article = next(a for a in data["articles"] if a.get("id") == SLUG)
                self.assertEqual(article["image"], URL)

    def test_public_text_has_no_private_repository_raw_links(self):
        for p in ROOT.rglob("*"):
            if p.suffix.lower() not in (".html", ".json", ".js", ".css"):
                continue
            with self.subTest(path=str(p.relative_to(ROOT))):
                content = p.read_text(encoding="utf-8")
                self.assertFalse(
                    "raw.githubusercontent.com/TrueBinary/raven-crow-biblioteca" in content,
                    f"Private GitHub Raw URL in {p.relative_to(ROOT)}",
                )


if __name__ == "__main__":
    unittest.main()
