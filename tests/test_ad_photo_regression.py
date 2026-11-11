import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

class AdPhotoRegressionTests(unittest.TestCase):
    def test_home_ad_is_static_in_editorial_sidebar_without_duplicate_tag(self):
        page=(ROOT/'index.html').read_text(encoding='utf-8')
        content=page[page.index('id="editorial-feed"'):page.index('</section>',page.index('id="editorial-feed"'))]
        self.assertIn('class="rc-mag-side"',content)
        self.assertIn('class="rc-ad-slot',content)
        self.assertIn('https://bauval.org/22/5852535d1154a53ec6291a417f88e211',content)
        self.assertEqual(page.count('bauval.org/22/5852535d1154a53ec6291a417f88e211'),1)
        js=(ROOT/'public/raven-frontpage.js').read_text(encoding='utf-8')
        self.assertNotIn('side.append(existingAd)',js)
        self.assertNotIn("root.textContent=''",js)

    def test_wikimedia_thumbnail_host_and_commercial_cc_by_2(self):
        from editorial_photos import choose_candidate
        article={'title':'Bandeira Brasil Noruega','id':'flag-news'}
        c={'title':'File:Bandeira Brasil Noruega.jpg','license':'CC BY 2.0','url':'https://thumb.wikimedia.org/wikipedia/commons/thumb/1/12/bandeira.jpg','page':'https://commons.wikimedia.org/wiki/File:Bandeira_Brasil_Noruega.jpg','width':1200,'height':800,'artist':'Photographer'}
        self.assertEqual(choose_candidate(article,[c]),c)

    def test_curated_news_uses_exact_file_lookup(self):
        from editorial_photos import fetch_photos, CURATED_FILES
        slug='eleicoes-2026'
        self.assertIn(slug,CURATED_FILES)
        c={'title':CURATED_FILES[slug],'license':'Public domain','url':'https://upload.wikimedia.org/wikipedia/commons/2/22/urna.jpg','page':'https://commons.wikimedia.org/wiki/File:Brazilian_DRE_voting_machine_for_2022_elections.jpg','width':1200,'height':850,'artist':'Arquivo'}
        with TemporaryDirectory() as t:
            with patch('editorial_photos.lookup_commons',return_value=c),patch('editorial_photos.download_photo',return_value=b'\\xff\\xd8\\xff'+b'0'*5000):
                photos=fetch_photos(Path(t),[{'id':slug,'title':'Após a eleição, o voto confere poder ou impõe limites?'}])
            self.assertEqual(photos[slug]['commons_title'],CURATED_FILES[slug])
            self.assertTrue((Path(t)/photos[slug]['path']).exists())

    def test_news_cards_do_not_use_text_covers_as_photos(self):
        js=(ROOT/'public/raven-frontpage.js').read_text(encoding='utf-8')
        self.assertNotIn("'carrosseis/'+folder+'/slide1.png'",js)
        self.assertNotIn("(assets.covers&&assets.covers[a.id])",js)
        self.assertIn('raven-logo.webp',js)

    def test_visible_photo_credits_page(self):
        self.assertTrue((ROOT/'public/creditos-fotos.html').exists())
        js=(ROOT/'public/raven-frontpage.js').read_text(encoding='utf-8')
        self.assertIn("'/creditos-fotos'",js)

    def test_seven_existing_articles_have_relevant_jpeg_sources(self):
        import json
        from editorial_photos import LICENSES
        public=ROOT/'public'
        credits=json.loads((public/'editorial-photo-credits.json').read_text(encoding='utf-8'))
        stories=json.loads((public/'editorial-feed.json').read_text(encoding='utf-8'))['articles']
        for article in stories:
            slug=article['id']
            if slug not in credits: continue  # sem foto: a capa usa o logo (raven-logo.webp, testado acima)
            record=credits[slug]
            if record.get('commons_title'):  # escolhida pelo seletor automático do Wikimedia
                self.assertIn(record['license'],LICENSES)
                self.assertTrue(record['source'].startswith('https://commons.wikimedia.org/'))
            else:  # mandada pelo agente (pasta ou campo photos): licença e crédito livres, mas obrigatórios
                self.assertTrue(record['license'].strip() and record['artist'].strip(),slug)
                self.assertTrue(record['source'].startswith('https://'),slug)
            photo=public/record['path']
            self.assertTrue(photo.exists(),str(photo))
            self.assertGreater(photo.stat().st_size,1024)
            self.assertTrue(photo.read_bytes().startswith(bytes([255,216,255])))

    def test_no_fill_fallback_and_auto_publish_are_connected(self):
        html=(ROOT/'index.html').read_text(encoding='utf-8')
        news=(ROOT/'public/noticias.html').read_text(encoding='utf-8')
        fallback=(ROOT/'public/raven-ad-visibility.js').read_text(encoding='utf-8')
        workflow=(ROOT/'.github/workflows/site-release.yml').read_text(encoding='utf-8')
        self.assertIn('raven-ad-visibility.js',html)
        self.assertIn('raven-ad-visibility.js',news)
        self.assertIn("slot.classList.add('rc-ad-unfilled')",fallback)
        self.assertIn('editorial/photos',workflow)
        self.assertIn('creditos-fotos.html',workflow)

if __name__=='__main__':unittest.main()
