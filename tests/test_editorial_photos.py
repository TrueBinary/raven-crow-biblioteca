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
if __name__=='__main__':unittest.main()
