import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
from editorial_photos import choose_candidate, fetch_photos

class EditorialPhotoTests(unittest.TestCase):
 def test_requires_relevant_title_and_permissive_license(self):
  a={'title':'Mercosul e EFTA fecham acordo','id':'mercosul-efta'}
  good={'title':'File:Mercosul EFTA agreement.jpg','license':'CC BY-SA 4.0','url':'https://upload.wikimedia.org/wikipedia/commons/a/ab/mercosul.jpg','page':'https://commons.wikimedia.org/wiki/File:Mercosul_EFTA_agreement.jpg','width':1200,'height':800,'artist':'Photographer'}
  self.assertEqual(choose_candidate(a,[good]),good)
  self.assertIsNone(choose_candidate(a,[dict(good,title='File:random person.jpg')]))
  self.assertIsNone(choose_candidate(a,[dict(good,license='All rights reserved')]))
 def test_uses_fallback_without_network(self):
  with TemporaryDirectory() as t:
   with patch('editorial_photos.search_commons',return_value=[]):
    result=fetch_photos(Path(t),[{'id':'some-news','title':'Some news headline'}])
   self.assertEqual(result,{})
 def test_writes_attribution_and_downloads(self):
  good={'title':'File:Mercosul EFTA agreement.jpg','license':'CC BY-SA 4.0','url':'https://upload.wikimedia.org/wikipedia/commons/a/ab/mercosul.jpg','page':'https://commons.wikimedia.org/wiki/File:Mercosul_EFTA_agreement.jpg','width':1200,'height':800,'artist':'Photographer'}
  with TemporaryDirectory() as t:
   with patch('editorial_photos.search_commons',return_value=[good]),patch('editorial_photos.download_photo',return_value=b'\xff\xd8\xff'+b'0'*5000):
    result=fetch_photos(Path(t),[{'id':'mercosul-efta','title':'Mercosul e EFTA fecham acordo'}])
   self.assertIn('mercosul-efta',result)
   self.assertEqual(result['mercosul-efta']['license'],'CC BY-SA 4.0')
 def test_updates_cached_photo_if_curated_source_changed(self):
  import json
  from editorial_photos import CURATED_FILES
  slug='eleicoes-2026'
  correct=CURATED_FILES[slug]
  candidate={'title':correct,'license':'Public domain','url':'https://upload.wikimedia.org/wikipedia/commons/a/ab/urna.jpg','page':'https://commons.wikimedia.org/wiki/File:Brazilian_DRE_voting_machine_for_2022_elections.jpg','width':1200,'height':800,'artist':'Archive'}
  with TemporaryDirectory() as t:
   p=Path(t); folder=p/'editorial'/'photos';folder.mkdir(parents=True)
   (folder/(slug+'.jpg')).write_bytes(b'old')
   (p/'editorial-photo-credits.json').write_text(json.dumps({slug:{'path':'editorial/photos/'+slug+'.jpg','commons_title':'File:Old unrelated photo.jpg'}}),encoding='utf-8')
   with patch('editorial_photos.lookup_commons',return_value=candidate),patch('editorial_photos.download_photo',return_value=b'\\xff\\xd8\\xff'+b'0'*5000):
    result=fetch_photos(p,[{'id':slug,'title':'Após eleição'}])
   self.assertEqual(result[slug]['commons_title'],correct)
   self.assertGreater((folder/(slug+'.jpg')).stat().st_size,1000)
if __name__=='__main__':unittest.main()
