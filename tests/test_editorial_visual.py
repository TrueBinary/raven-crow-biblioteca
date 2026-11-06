import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class VisualFidelity(unittest.TestCase):
 def test_desktop_one_row_mobile_two_rows(self):
  css=(ROOT/'public/raven-navigation.css').read_text(encoding='utf-8')
  self.assertIn('@media(min-width:901px)',css)
  self.assertIn('.rc-global-tools .rc-menu-toggle{display:none}',css)
  self.assertIn('border-top:0;min-height:76px',css)
 def test_article_images_and_metadata(self):
  js=(ROOT/'public/raven-frontpage.js').read_text(encoding='utf-8')
  self.assertIn('rc-mag-hero-image',js)
  self.assertIn('rc-mag-item-image',js)
  self.assertIn('readingTime',js)
  self.assertIn('imagePath',js)
 def test_archived_articles_in_frontpage_feed(self):
  import json
  data=json.loads((ROOT/'public/editorial-feed.json').read_text(encoding='utf-8'))
  self.assertGreaterEqual(len(data['articles']),6)
  self.assertEqual(len({a['id'] for a in data['articles']}),len(data['articles']))
 def test_photo_responsive_styles(self):
  css=(ROOT/'public/raven-unified.css').read_text(encoding='utf-8')
  self.assertIn('.rc-mag-hero-image',css)
  self.assertIn('.rc-mag-item-image',css)
  self.assertIn('.rc-mag-hero-content',css)
if __name__=='__main__':unittest.main()
