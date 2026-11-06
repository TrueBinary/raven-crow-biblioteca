import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class MobileRegression(unittest.TestCase):
 def test_navigation_overrides_old_mobile_hide(self):
  css=(ROOT/'public/raven-navigation.css').read_text(encoding='utf-8')
  self.assertIn('.rc-global-nav a:not(.top-cta){display:inline-flex',css)
 def test_hero_does_not_overlay_text_on_generated_cover(self):
  js=(ROOT/'public/raven-frontpage.js').read_text(encoding='utf-8')
  self.assertIn('assets.photos&&assets.photos[lead.id]',js)
  self.assertIn('rc-mag-hero-image',js)
 def test_mobile_title_legible(self):
  css=(ROOT/'public/raven-unified.css').read_text(encoding='utf-8')
  self.assertIn('.rc-mag-hero-content h2{font-size:clamp(30px,7.5vw,42px)',css)
if __name__=='__main__':unittest.main()
