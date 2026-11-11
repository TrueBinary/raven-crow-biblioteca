"""Build the news index using the same shared header, cards and licensed photos as the homepage."""
from pathlib import Path
from html import escape
import json
import re

ROOT=Path(__file__).resolve().parent
PUBLIC=ROOT/'public'
home=(ROOT/'index.html').read_text(encoding='utf-8')
header=re.search(r'<header class="rc-global-header">.*?</header>',home,re.S)
ad=re.search(r'<aside class="rc-ad-slot rc-ad-desktop".*?</aside>',home,re.S)
if not header or not ad:
    raise RuntimeError("Homepage shared header or approved static Adsterra slot missing")
feed=json.loads((PUBLIC/'editorial-feed.json').read_text(encoding='utf-8'))
articles=feed.get('articles',[])
ids=set()
links=[]
for article in articles:
    slug=str(article.get('id',''))
    if not re.fullmatch(r'[a-z0-9-]{3,100}',slug) or slug in ids:continue
    ids.add(slug)
    links.append('<li><a href="noticias/'+escape(slug)+'/" aria-label="Abrir matéria: '+escape(article.get('title',''),quote=True)+'">'+escape(article.get('title',''))+'</a> <span>('+escape(article.get('date',''))+')</span></li>')
page='''<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#090a0c">
<meta name="description" content="Acompanhe todas as matérias, análises políticas e notícias do Raven Crow em um só lugar, com acesso ao arquivo e às fontes.">
<link rel="canonical" href="https://ravencrow.cloud/noticias.html">
<meta property="og:type" content="website"><meta property="og:title" content="Notícias e análises | Raven Crow">
<meta property="og:description" content="Notícias, contexto e análises com acesso ao arquivo de matérias do Raven Crow.">
<meta property="og:url" content="https://ravencrow.cloud/noticias.html">
<title>Notícias e análises | Raven Crow</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=DM+Sans:wght@400;500;600;700;800&display=swap">
<link rel="stylesheet" href="raven-navigation.css"><link rel="stylesheet" href="raven-unified.css"><link rel="stylesheet" href="raven-news.css">
<script defer src="raven-navigation.js"></script><script defer src="raven-ad-visibility.js"></script>
</head><body class="rc-news-index">'''+header.group(0)+'''
<main id="main-content">
<section class="rc-news-intro" aria-labelledby="rc-news-heading">
<p class="rc-news-eyebrow">RAVEN CROW / O CORVO INVESTIGADOR</p>
<h1 id="rc-news-heading">NOTÍCIAS <em>&amp; ANÁLISES.</em></h1>
<div class="rc-news-intro-bar"><p>Todas as publicações, da edição atual ao arquivo. Matérias com contexto, fontes e análise editorial.</p>
<span id="news-count" role="status" aria-live="polite">Carregando acervo...</span></div>
</section>
<section class="rc-magazine" id="editorial-feed" data-feed-mode="all" aria-label="Acervo completo de notícias">
<div class="rc-mag-main"><p>Carregando matérias...</p></div>
<div class="rc-mag-side">'''+ad.group(0)+'''</div>
</section>
<noscript><section class="rc-news-noscript"><h2>Arquivo de notícias</h2><ul>'''+''.join(links)+'''</ul></section></noscript>
<section class="rc-news-next"><div><span>MAIS CONTEXTO</span><h2>Uma notícia abre perguntas. A leitura aprofunda.</h2><p>Conheça os ensaios do Corvo Investigador e a nossa seleção de livros.</p></div>
<nav aria-label="Explorar mais"><a href="coluna.html">Ler a coluna</a><a href="livros.html">Conhecer livros</a></nav></section>
</main><footer class="rc-news-footer">© Raven Crow · <a href="coluna.html">Coluna do Corvo</a> · <a href="sobre.html">Sobre</a> · <a href="privacidade.html">Privacidade</a> · <a href="termos.html">Termos</a></footer>
<script defer src="raven-frontpage.js"></script><script defer src="raven-analytics.js"></script>
</body></html>'''
(PUBLIC/'noticias.html').write_text(page,encoding='utf-8')
# Homepage: plain links to the newest articles inside .rc-mag-main, so crawlers find them without running JS.
# raven-frontpage.js empties .rc-mag-main and draws the magazine on top, so the visible page does not change.
latest=sorted((a for a in articles if re.fullmatch(r'[a-z0-9-]{3,100}',str(a.get('id','')))),key=lambda a:a.get('date',''),reverse=True)[:12]
static='<ul class="rc-static-links">'+''.join(f'<li><a href="noticias/{escape(a["id"],quote=True)}/">{escape(a.get("title",""))}</a></li>' for a in latest)+'</ul>'
home_now=(ROOT/'index.html').read_text(encoding='utf-8')
home_new=re.sub(r'<div class="rc-mag-main">(?:<ul class="rc-static-links">.*?</ul>)?</div>',lambda m:'<div class="rc-mag-main">'+static+'</div>',home_now,count=1,flags=re.S)
if 'rc-static-links' not in home_new:raise RuntimeError('Homepage .rc-mag-main container missing')
# Preload the lead story's photo so the browser finds the LCP image in the HTML instead of after JS + feed fetch.
# Must pick the same story and sizes as raven-frontpage.js (first valid article, photo from editorial-images.json).
images=json.loads((PUBLIC/'editorial-images.json').read_text(encoding='utf-8'))
lead=next((a for a in articles if re.fullmatch(r'[a-z0-9-]{3,100}',str(a.get('id','')))),{})
v=None if lead.get('image') else images.get('photoVariants',{}).get(lead.get('id'))
preload=(f'<link rel="preload" as="image" data-rc-lead href="{escape(v["src"],quote=True)}" imagesrcset="{escape(v["srcset"],quote=True)}" '
         'imagesizes="(max-width: 900px) 100vw, 900px" fetchpriority="high">') if v else ''
home_new=re.sub(r'<link rel="preload" as="image" data-rc-lead[^>]*>','',home_new)
home_new=home_new.replace('</head>',preload+'</head>',1)
from newsletter import block as newsletter_block
nl=newsletter_block('home')
home_new=re.sub(r'<!-- rc-newsletter:start -->.*?<!-- rc-newsletter:end -->',lambda m:'<!-- rc-newsletter:start -->'+(f'<div class="wrap">{nl}</div>' if nl else '')+'<!-- rc-newsletter:end -->',home_new,count=1,flags=re.S)
if home_new!=home_now:(ROOT/'index.html').write_text(home_new,encoding='utf-8')
from raven_seo import build as build_seo
build_seo(ROOT)
print(f'News index generated with {len(links)} published article links')
