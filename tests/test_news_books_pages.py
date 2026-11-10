import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'public'

class NewsAndBooksTests(unittest.TestCase):
 def test_news_page_uses_homepage_design_and_all_archive(self):
  html=(PUBLIC/'noticias.html').read_text(encoding='utf-8')
  js=(PUBLIC/'raven-frontpage.js').read_text(encoding='utf-8')
  for marker in ['data-feed-mode="all"','id="editorial-feed"','raven-unified.css','raven-frontpage.js','rc-mag-main','rc-mag-side','rc-global-header','raven-ad-visibility.js']:
   self.assertIn(marker,html,marker)
  self.assertIn("root.dataset.feedMode==='all'",js)
  self.assertIn("fetch('editorial-feed.json'",js)
  self.assertIn("new URLSearchParams(location.search)",js)
  self.assertIn('hero.id=lead.id',js)
  self.assertIn('link.id=a.id',js)
  self.assertNotIn("fetch('noticias.json'",html)
 def test_news_articles_all_present_without_deduplication_loss(self):
  feed=json.loads((PUBLIC/'editorial-feed.json').read_text(encoding='utf-8'))['articles']
  self.assertGreaterEqual(len(feed),7)
  self.assertEqual(len(feed),len({a['id'] for a in feed}))
  html=(PUBLIC/'noticias.html').read_text(encoding='utf-8')
  for article in feed:
   self.assertIn('noticias/'+article['id']+'/',html)
 def test_books_imported_from_home_in_full(self):
  home=(ROOT/'index.html').read_text(encoding='utf-8')
  src=re.search(r'const books = (\[.*?\]);\s*function amazonUrl',home,re.S)
  self.assertIsNotNone(src)
  original=json.loads(src.group(1))
  imported=json.loads((PUBLIC/'livros.json').read_text(encoding='utf-8'))['books']
  self.assertEqual(len(original),len(imported))
  self.assertEqual({x['id'] for x in original},{x['id'] for x in imported})
  for book in imported:
   self.assertGreaterEqual(len(book.get('whyRead','')),75,book['id'])
   self.assertEqual(book['title'],next(x['title'] for x in original if x['id']==book['id']))
 def test_book_page_marketing_copy_and_accessible_filter(self):
  html=(PUBLIC/'livros.html').read_text(encoding='utf-8')
  js=(PUBLIC/'raven-books.js').read_text(encoding='utf-8')
  for marker in ['raven-books.css','raven-books.js','id="book-grid"','Por que vale a leitura','Divulgação de afiliados','raven-navigation.css']:
   self.assertIn(marker,html,marker)
  for marker in ["fetch('livros.json'",'amazon.com.br/s','new URLSearchParams','whyRead','aria-pressed']:
   self.assertIn(marker,js,marker)
  self.assertNotIn('R$ 99',html)
 def test_build_pipeline_includes_pages_and_agent_rules(self):
  workflow=(ROOT/'ops/cloudflare/release-local.ps1').read_text(encoding='utf-8')
  editorial=(ROOT/'EDITORIAL.md').read_text(encoding='utf-8')
  for marker in ['build-news-index.py','build-library.py','public/livros.json','public/noticias.html']:
   self.assertIn(marker,workflow,marker)
  for marker in ['coluna-ensaios.json','Política e sociedade','Filosofia e ideias','Fé e família','arquivo','livros.json']:
   self.assertIn(marker,editorial,marker)

if __name__=='__main__':
 unittest.main()
