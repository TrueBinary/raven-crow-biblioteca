from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class AdLayoutTest(unittest.TestCase):
 def test_banner_on_news(self):
  s=(ROOT/'public/noticias.html').read_text(encoding='utf-8')
  self.assertIn('5852535d1154a53ec6291a417f88e211',s)
  self.assertIn('Publicidade',s)
 def test_banner_on_home(self):
  s=(ROOT/'index.html').read_text(encoding='utf-8')
  self.assertIn('5852535d1154a53ec6291a417f88e211',s)
 def test_shared_header(self):
  home=(ROOT/'index.html').read_text(encoding='utf-8')
  news=(ROOT/'public/noticias.html').read_text(encoding='utf-8')
  self.assertIn('class="rc-global-header"',news)
  self.assertIn('class="rc-global-nav"',news)
  self.assertIn('raven-unified.css',home)
  self.assertIn('raven-unified.css',news)
if __name__=='__main__':unittest.main()
