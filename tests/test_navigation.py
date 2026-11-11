import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class NavigationTests(unittest.TestCase):
 def test_all_pages_exist_and_linked(self):
  for name in ['index','noticias','coluna','livros','apoie','sobre']:
   path=ROOT/'public'/f'{name}.html' if name!='index' else ROOT/'index.html'
   self.assertTrue(path.exists(),str(path))
   s=path.read_text(encoding='utf-8')
   for link in ['/noticias','/coluna','/livros','/apoie','/sobre']:
    self.assertIn('href="'+link+'"',s)
   self.assertIn('raven-navigation.css',s)
   self.assertIn('raven-navigation.js',s)
 def test_mobile_controls(self):
  for name in ['index.html','public/noticias.html']:
   s=(ROOT/name).read_text(encoding='utf-8')
   self.assertIn('class="rc-search-toggle"',s)
   self.assertIn('class="rc-menu-toggle"',s)
 def test_sitemap_includes_navigation_pages(self):
  s=(ROOT/'public/sitemap.xml').read_text(encoding='utf-8')
  for page in ['coluna','livros','apoie','sobre']:
   self.assertIn('<loc>https://ravencrow.cloud/'+page+'</loc>',s)
 def test_support_link(self):
  s=(ROOT/'public/apoie.html').read_text(encoding='utf-8')
  self.assertIn('https://pixgg.com/ravencrow',s)
if __name__=='__main__':unittest.main()
