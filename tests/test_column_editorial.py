import unittest
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'public'

class ColumnEditorialTests(unittest.TestCase):
 def test_column_hub_has_three_editorial_tracks(self):
  s=(PUBLIC/'coluna.html').read_text(encoding='utf-8')
  for phrase in ('Política e sociedade','Filosofia e ideias','Fé e família','Arquivo de análises'):
   self.assertIn(phrase,s)
  self.assertIn('raven-column.js',s)
  self.assertIn('raven-column.css',s)
  self.assertIn('class="rc-global-header"',s)
 def test_hub_links_every_essay_in_html(self):
  # SEO: ensaio sem link no HTML do hub fica órfão; o Google só o acharia pelo sitemap
  s=(PUBLIC/'coluna.html').read_text(encoding='utf-8')
  essays=json.loads((PUBLIC/'coluna-ensaios.json').read_text(encoding='utf-8'))['essays']
  missing=[e['id'] for e in essays if f'href="coluna/{e["id"]}/"' not in s]
  self.assertEqual(missing,[])
 def test_three_opinion_articles_are_readable(self):
  data=json.loads((PUBLIC/'coluna-ensaios.json').read_text(encoding='utf-8'))['essays']
  self.assertGreaterEqual(len(data),3)
  for a in data:
   path=PUBLIC/'coluna'/a['id']/'index.html'
   self.assertTrue(path.is_file(),str(path))
   s=path.read_text(encoding='utf-8')
   self.assertIn(a['title'],s)
   self.assertIn('Opinião',s)
   self.assertIn('Fontes e leituras',s)
   self.assertIn('raven-column.css',s)
   self.assertIn('href="/coluna"',s)
 def test_existing_articles_survive_and_feed_is_dynamic(self):
  data=json.loads((PUBLIC/'editorial-feed.json').read_text(encoding='utf-8'))['articles']
  self.assertGreaterEqual(len(data),7)
  js=(PUBLIC/'raven-column.js').read_text(encoding='utf-8')
  self.assertIn("fetch('/editorial-feed.json'",js)
  self.assertIn("noticias/",js)
  self.assertIn('root.replaceChildren()',js)
 def test_family_piece_cites_original_catholic_sources_and_is_labeled_opinion(self):
  data=json.loads((PUBLIC/'coluna-ensaios.json').read_text(encoding='utf-8'))['essays']
  family=next(a for a in data if a['id']=='familia-crista-primeira-escola-de-amor')
  self.assertIn('família',family['title'].lower())
  self.assertTrue(any(s['url'].startswith('https://www.vatican.va/') for s in family['sources']))
  self.assertGreaterEqual(len(family['paragraphs']),4)
 def test_essays_are_indexed(self):
  sitemap=(PUBLIC/'sitemap.xml').read_text(encoding='utf-8')
  data=json.loads((PUBLIC/'coluna-ensaios.json').read_text(encoding='utf-8'))['essays']
  for essay in data:
   self.assertIn('https://ravencrow.cloud/coluna/'+essay['id']+'/',sitemap)
 def test_publishing_workflow_updates_column_pages(self):
  # o pipeline vive no workflow Publicar site desde 10/11/2026
  s=(ROOT/'.github/workflows/site-release.yml').read_text(encoding='utf-8')
  self.assertIn('build-column.py',s)
  self.assertIn('public/coluna.html',s)
  self.assertIn('public/coluna',s)

if __name__=='__main__':unittest.main()
