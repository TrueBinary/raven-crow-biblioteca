from pathlib import Path
import json,html,re,os
from editorial_covers import build_covers
from editorial_photos import fetch_photos, render_credits_page
from column_photos import webp_variants
from raven_seo import stamp_first_seen
from newsletter import block as newsletter_block
from news_photos import news_figures
from news_videos import news_videos
from news_i18n import LANGS, langs_of, hreflang, url_of, render_article as render_tr_article, render_index as render_tr_index
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parent
BASE='https://ravencrow.cloud'
pix='https://pixgg.com/ravencrow'
root=ROOT/'index.html'; news=ROOT/'public/noticias.html'
def patch(path,fn):
    s=path.read_text(encoding='utf-8')
    t=fn(s)
    if s!=t:path.write_text(t,encoding='utf-8')
def common(s,is_news):
    if 'raven-analytics.js' not in s:
        src='raven-analytics.js'
        s=s.replace('</body>',f'<script defer src="{src}"></script></body>',1)
    if 'rel="canonical"' not in s:
        target=BASE+('/noticias.html' if is_news else '/')
        s=s.replace('</head>',f'<link rel="canonical" href="{target}"><meta property="og:url" content="{target}"></head>',1)
    return s
def library(s):
    s=common(s,False)
    if 'id="apoie"' not in s:
        section='''<section id="apoie" class="support-band" aria-labelledby="support-title"><div class="wrap support-inner"><div><span class="kicker">APOIE O JORNALISMO INDEPENDENTE</span><h2 id="support-title">AJUDE O CORVO A INVESTIGAR.</h2><p>Seu apoio mantém as análises, a curadoria e a biblioteca disponíveis. O Pix é voluntário; não é necessário para acessar o conteúdo.</p></div><a class="btn btn-primary" href="https://pixgg.com/ravencrow" target="_blank" rel="noopener noreferrer" data-track="pix" data-placement="biblioteca-destaque">Apoiar via Pix ↗</a></div></section>'''
        s=s.replace('<section class="wrap intro"',section+'<section class="wrap intro"',1)
        s=s.replace('</style>','''.support-band{background:#24191c;border-block:1px solid #854a45;padding:38px 0}.support-inner{display:flex;align-items:center;justify-content:space-between;gap:30px}.support-inner h2{font:900 clamp(30px,5vw,52px)/1 'Barlow Condensed',sans-serif;margin:12px 0}.support-inner p{color:#ded0ca;max-width:620px}.support-inner .btn{white-space:nowrap}@media(max-width:680px){.support-inner{flex-direction:column;align-items:flex-start}} </style>''',1)
    return s
def column(s):
    s=common(s,True)
    if 'id="apoie-coluna"' not in s:
        section='''<section id="apoie-coluna" class="container" style="padding-top:32px;padding-bottom:35px"><div style="background:#25191d;border:1px solid #88524b;border-radius:12px;padding:25px"><div class="eyebrow">MANTENHA A COLUNA INDEPENDENTE</div><h2 style="margin:10px 0">APOIE O CORVO VIA PIX.</h2><p>O conteúdo é gratuito. Seu apoio voluntário ajuda a manter a investigação e a curadoria de livros.</p><p><a href="https://pixgg.com/ravencrow" data-track="pix" data-placement="coluna-destaque" target="_blank" rel="noopener noreferrer" style="display:inline-block;background:#e55e49;color:#161217;padding:12px 20px;border-radius:8px;font-weight:800;text-decoration:none">Apoiar via Pix ↗</a> <a href="index.html#biblioteca" data-track="library" style="margin-left:15px">Conhecer os livros recomendados ↗</a></p></div></section>'''
        s=s.replace('<section class="container" id="edicao">',section+'<section class="container" id="edicao">',1)
    return s
patch(root,library);patch(news,column)

# Static SEO articles, preserving news.json as the single source of truth.
data=json.loads((ROOT/'public/noticias.json').read_text(encoding='utf-8'))
out=ROOT/'public/noticias';out.mkdir(exist_ok=True)
# Identidade dos carrosséis: título condensado com a palavra-chave em vermelho e o resto do título abaixo
def title_html(t):
    m=re.match(r'(.+?[:?])\s*(.*)$',t)
    head,rest=(m.group(1).rstrip(':'),m.group(2)) if m else (t,'')
    first,_,last=head.rpartition(' ')
    big=(html.escape(first)+' ' if first else '')+'<em>'+html.escape(last)+'</em>'
    return big+('<span class="rc-h1-sub">'+html.escape(rest)+'</span>' if rest else '')
MESES=['JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ']
def br_date(d):
    y,m,dd=str(d).split('-')[:3]
    return dd+' '+MESES[int(m)-1]+' '+y
RC_CSS=("body.rc-news{margin:0;min-height:100vh;background:#0a0a0b radial-gradient(ellipse at 85% 0%,#2b0e11 0%,transparent 55%) fixed;color:#f4f1ec;font:17px/1.75 'DM Sans',system-ui,sans-serif;border-left:12px solid #d7262b}"
 ".rc-news a{color:#ff6b5f}.rc-news a:focus-visible{outline:3px solid #ff6b5f;outline-offset:3px}"
 ".rc-top,.rc-news main,.rc-foot{max-width:860px;margin:0 auto;padding-left:24px;padding-right:24px}"
 ".rc-top{display:flex;align-items:center;gap:22px;padding-top:26px}"
 ".rc-line{flex:1;display:flex;align-items:center;gap:20px;border-bottom:1px solid #4a1d20;padding-bottom:12px}"
 ".rc-brand{display:flex;align-items:center;gap:12px;white-space:nowrap;color:#f4f1ec!important;text-decoration:none;font:800 27px/1 'Barlow Condensed',Impact,sans-serif;letter-spacing:.02em}"
 ".rc-brand i{width:22px;height:8px;background:#d7262b}"
 ".rc-line nav{margin-left:auto;display:flex;gap:16px}.rc-line nav a{color:#b9b3ad;text-decoration:none;font:700 12px 'DM Sans',sans-serif;letter-spacing:.08em;text-transform:uppercase}.rc-line nav a:hover{color:#fff}"
 ".rc-logo{width:56px;height:56px;border-radius:50%;border:2px solid #7a1c20;padding:4px;flex:none}"
 ".rc-news main{padding-top:44px;padding-bottom:70px}"
 ".rc-pill{display:inline-block;background:#5b1519;color:#f6e9e6;font:700 13px/1 'DM Sans',sans-serif;letter-spacing:.06em;text-transform:uppercase;padding:10px 14px;border-radius:4px}"
 ".rc-news h1{font:900 clamp(50px,9vw,98px)/.92 'Barlow Condensed',Impact,sans-serif;text-transform:uppercase;letter-spacing:-.005em;margin:26px 0 0}"
 ".rc-news h1 em,.rc-news h2 em{font-style:normal;color:#e0262c}"
 ".rc-h1-sub{display:block;margin-top:14px;font-size:clamp(27px,4.2vw,42px);line-height:1.02;color:#d9d3cd}"
 ".rc-news h1:after{content:'';display:block;width:180px;max-width:40%;height:8px;background:#d7262b;margin-top:24px}"
 ".rc-news main>p:first-of-type{font-size:clamp(19px,2.4vw,23px);line-height:1.5}.rc-news main>p:first-of-type strong{font-weight:500}"
 ".rc-news h2{font:900 clamp(34px,5vw,52px)/1 'Barlow Condensed',Impact,sans-serif;text-transform:uppercase;margin:54px 0 12px;padding-top:26px;border-top:1px solid #3a1a1c}"
 ".rc-news main ul{list-style:none;padding:0}.rc-news main li{padding:11px 0;border-bottom:1px solid #26262a}.rc-news main li a{color:#f4f1ec;text-decoration-color:#d7262b;text-underline-offset:4px}"
 ".rc-news .cta{margin-top:50px;padding:28px;background:#150c0e;border:1px solid #4f1418;border-left:6px solid #d7262b;border-radius:6px}.rc-news .cta h2{margin:0 0 6px;padding:0;border:0;font-size:clamp(30px,4vw,40px)}"
 ".rc-news .btn{display:inline-flex;align-items:center;gap:12px;background:#c8202a;color:#fff;text-decoration:none;font:800 14px/1.25 'DM Sans',sans-serif;letter-spacing:.05em;text-transform:uppercase;padding:14px 20px;border-radius:6px}.rc-news .btn:hover{background:#e0262c}"
 ".rc-foot{display:flex;justify-content:space-between;gap:16px;padding-top:22px;padding-bottom:40px;border-top:1px solid #3a1a1c;font:600 12px 'DM Sans',sans-serif;letter-spacing:.08em;text-transform:uppercase;color:#cfc9c3}.rc-foot b{color:#e0262c;font-weight:800}"
 "@media(max-width:640px){body.rc-news{border-left-width:6px}.rc-top{padding-top:18px}.rc-logo{width:44px;height:44px}.rc-line nav{display:none}.rc-foot{flex-direction:column}}")
urls=[BASE+'/',BASE+'/noticias.html']+[BASE+'/'+name+'.html' for name in ('coluna','livros','apoie','sobre')]
# Edição atual primeiro, depois o arquivo do mais recente ao mais antigo: o primeiro id visto prevalece.
editions=[data]+[json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'public/arquivo').glob('noticias-*.json'),reverse=True)]
articles={}
for ed in editions:
    for a in ed.get('articles',[]):articles.setdefault(a.get('id'),(a,ed.get('updatedAt','')))
all_news_articles=[a for a,_ in articles.values()]
photo_credits=fetch_photos(ROOT/'public',all_news_articles)
render_credits_page(ROOT/'public',photo_credits,all_news_articles)
(ROOT/'public/editorial-images.json').write_text(json.dumps({'carousels':sorted(p.parent.name for p in (ROOT/'public/carrosseis').glob('*/slide1.png')),'covers':build_covers(ROOT/'public',all_news_articles),'photos':{k:v['path'] for k,v in photo_credits.items()},'photoVariants':{k:pv for k,v in photo_credits.items() if re.fullmatch(r'editorial/photos/[a-z0-9-]+\.jpg',v.get('path','')) and (pv:=webp_variants(ROOT/'public',v['path']))}},ensure_ascii=False,indent=2),encoding='utf-8')
stamp_first_seen(ROOT/'public/editorial-feed.json',articles.values())  # antes de sobrescrever o feed
(ROOT/'public/editorial-feed.json').write_text(json.dumps({'articles':[a for a,_ in sorted(articles.values(),key=lambda pair:pair[0].get('date',''),reverse=True)]},ensure_ascii=False,indent=2),encoding='utf-8')
for a,updated in articles.values():
    slug=str(a.get('id') or '')
    if not re.fullmatch(r'[a-z0-9-]{3,100}',slug):continue
    dest=out/slug;dest.mkdir(exist_ok=True)
    url=BASE+'/noticias/'+slug+'/'
    urls.append(url)
    esc=lambda v:html.escape(str(v or ''),quote=True)
    sources=''.join('<li><a rel="noopener noreferrer" target="_blank" href="'+esc(s['url'])+'">'+esc(s.get('name','Fonte'))+'</a></li>' for s in a.get('sources',[]) if urlparse(s.get('url','')).scheme=='https')
    figs=news_figures(slug,photo_credits,ROOT/'public',a['title'],prefix='../../')
    vids=news_videos(a,prefix='../../')
    figs={k:figs[k]+vids[k] for k in figs}
    schema={'@context':'https://schema.org','@type':'Article','headline':a['title'],'description':a.get('subtitle',''),'datePublished':a['date'],'dateModified':updated,'author':{'@type':'Organization','name':'Raven Crow'},'publisher':{'@type':'Organization','name':'Raven Crow'},'mainEntityOfPage':url,'isAccessibleForFree':True}
    page='''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0d0e12"><title>'''+esc(a['title'])+''' | Coluna do Corvo</title><meta name="description" content="'''+esc(a.get('subtitle','')[:155])+'''"><link rel="canonical" href="'''+url+'''"><meta property="og:type" content="article"><meta property="og:title" content="'''+esc(a['title'])+'''"><meta property="og:description" content="'''+esc(a.get('subtitle',''))+'''"><meta property="og:url" content="'''+url+'''"><script type="application/ld+json">'''+json.dumps(schema,ensure_ascii=False).replace('<','\\u003c')+'''</script><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@800;900&family=DM+Sans:wght@400;500;600;700;800&display=swap"><style>'''+RC_CSS+'''</style></head><body class="rc-news"><header class="rc-top"><div class="rc-line"><a class="rc-brand" href="../../index.html"><i aria-hidden="true"></i>RAVEN CROW</a><nav aria-label="Seções"><a href="../../noticias.html">Coluna do Corvo</a><a href="../../index.html#biblioteca">Biblioteca</a></nav></div><img class="rc-logo" src="../../raven-logo.webp" alt="" width="56" height="56"></header><main><span class="rc-pill">'''+esc(a.get('category','ANÁLISE'))+''' / Análise e opinião</span><h1>'''+title_html(a['title'])+'''</h1><p><strong>'''+esc(a.get('subtitle',''))+'''</strong></p>'''+figs['style']+figs['top']+'''<h2>O que <em>aconteceu</em></h2><p>'''+esc(a.get('facts',''))+'''</p>'''+figs['fatos']+'''<h2>Análise do <em>Corvo</em></h2><p>'''+esc(a.get('analysis',''))+'''</p>'''+figs['analise']+'''<h2><em>Contraponto</em></h2><p>'''+esc(a.get('counterpoint',''))+'''</p>'''+figs['contraponto']+'''<h2><em>Fontes</em></h2><ul>'''+sources+'''</ul><aside class="cta"><h2>Apoie o <em>Corvo</em></h2><p>Contribua voluntariamente via Pix ou conheça os livros recomendados na Biblioteca do Corvo.</p><a class="btn" href="'''+pix+'''" data-track="pix" data-placement="artigo">Apoiar via Pix <span aria-hidden="true">→</span></a> &nbsp; <a href="../../index.html#biblioteca" data-track="library">Ver livros ↗</a></aside>'''+newsletter_block('artigo')+'''</main><footer class="rc-foot"><span>O Corvo Investigador / <time datetime="'''+esc(a['date'])+'''">'''+br_date(a['date'])+'''</time></span><b>Raven Crow</b></footer><script defer src="../../raven-analytics.js"></script></body></html>'''
    tr={l:render_tr_article(ROOT,a,l,updated,photo_credits,RC_CSS,BASE,title_html) for l in langs_of(a)}
    urls.extend(tr.values())
    if tr:page=page.replace('<link rel="canonical" href="'+url+'">','<link rel="canonical" href="'+url+'">'+hreflang(url,tr),1)
    (dest/'index.html').write_text(page,encoding='utf-8')
for l in LANGS:urls.append(render_tr_index(ROOT,l,[a for a,_ in articles.values() if l in langs_of(a)],RC_CSS,BASE))
for essay in json.loads((ROOT/'public/coluna-ensaios.json').read_text(encoding='utf-8')).get('essays',[]):
    slug=str(essay.get('id',''))
    if re.fullmatch(r'[a-z0-9-]{6,100}',slug):urls.append(BASE+'/coluna/'+slug+'/')
from xml.sax.saxutils import escape
(ROOT/'public/sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join('<url><loc>'+escape(u)+'</loc></url>\n' for u in urls)+'</urlset>',encoding='utf-8')
(ROOT/'public/robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+BASE+'/sitemap.xml\n',encoding='utf-8')
# Apply the shared Raven Crow theme to regenerated article pages.
exec((ROOT/'apply-editorial-theme.py').read_text(encoding='utf-8'))
from raven_seo import build as build_seo
build_seo(ROOT)
print('Generated',len(urls)-2,'article pages; SEO, CTA and analytics hooks updated')
