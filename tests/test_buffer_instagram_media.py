"""The Buffer scheduled media must be publicly hosted by the Raven Crow site."""
import unittest
from pathlib import Path

PUBLIC = Path(__file__).resolve().parents[1] / "public" / "instagram-media"
IMAGES = (
    "ravencrow-graficos.png",
    "ravencrow-salario.png",
    "ravencrow-minerais-27.png",
    "ravencrow-estado-laico.png",
    "ravencrow-liberdade.png",
)

class BufferInstagramMediaTest(unittest.TestCase):
    def test_scheduled_images_exist_and_are_valid_pngs(self):
        for name in IMAGES:
            with self.subTest(name=name):
                path = PUBLIC / name
                self.assertTrue(path.is_file(), f"{name} missing")
                self.assertTrue(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), f"{name} invalid PNG")

if __name__ == "__main__":
    unittest.main()
