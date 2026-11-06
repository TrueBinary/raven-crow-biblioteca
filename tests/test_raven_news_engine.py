import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from raven_news_engine import score_crop, choose_crop, layout_headline, render_news
from PIL import Image
class NewsEngineTests(unittest.TestCase):
 def test_face_cut_is_hard_rejection(self):
  self.assertEqual(score_crop((0,0,100,100),[(90,30,110,60)],[]),float('inf'))
 def test_crop_prefers_protected_object(self):
  rect,cost=choose_crop((1600,900),(1080,760),[(1150,180,1450,620)],[])
  self.assertGreaterEqual(rect[2],1450)
 def test_no_valid_crop_fails_closed(self):
  with self.assertRaises(ValueError):choose_crop((1600,900),(1080,760),[(0,0,200,200),(1400,0,1600,200)],[])
 def test_long_headline_is_bounded(self):
  lines,size=layout_headline('TSE analisa uma ação sobre a chapa eleitoral de dois candidatos em Brasília e mais informações',950,365)
  self.assertLessEqual(len(lines)*size*1.03,365)
 def test_single_image_and_no_category(self):
  img=Image.new('RGB',(1500,1100),'#aaaaaa')
  result=render_news(img,'FILHA DO PRESIDENTE VIRALIZA COM CAMISETA','Uma imagem provoca debate.',[(480,100,1100,650)],[],None)
  self.assertEqual(result.size,(1080,1350))
 def test_reject_missing_protected_regions(self):
  with self.assertRaises(ValueError):render_news(Image.new('RGB',(1500,1100)),'TÍTULO','Resumo',None,[],None)
if __name__=='__main__':unittest.main()
