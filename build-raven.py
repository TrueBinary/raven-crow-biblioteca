from pathlib import Path
import json,html,re,os
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parent
BASE='https://raven-crow-biblioteca.onrender.com'
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
urls=[BASE+'/',BASE+'/noticias.html']
for a in data['articles']:
    slug=a['id']
    if not re.fullmatch(r'[a-z0-9-]{3,100}',slug):continue
    dest=out/slug;dest.mkdir(exist_ok=True)
    url=BASE+'/noticias/'+slug+'/'
    urls.append(url)
    esc=lambda v:html.escape(str(v or ''),quote=True)
    sources=''.join('<li><a rel="noopener noreferrer" target="_blank" href="'+esc(s['url'])+'">'+esc(s.get('name','Fonte'))+'</a></li>' for s in a.get('sources',[]) if urlparse(s.get('url','')).scheme=='https')
    schema={'@context':'https://schema.org','@type':'Article','headline':a['title'],'description':a.get('subtitle',''),'datePublished':a['date'],'dateModified':data['updatedAt'],'author':{'@type':'Organization','name':'Raven Crow'},'publisher':{'@type':'Organization','name':'Raven Crow'},'mainEntityOfPage':url,'isAccessibleForFree':True}
    page='''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0d0e12"><title>'''+esc(a['title'])+''' | Coluna do Corvo</title><meta name="description" content="'''+esc(a.get('subtitle','')[:155])+'''"><link rel="canonical" href="'''+url+'''"><meta property="og:type" content="article"><meta property="og:title" content="'''+esc(a['title'])+'''"><meta property="og:description" content="'''+esc(a.get('subtitle',''))+'''"><meta property="og:url" content="'''+url+'''"><script type="application/ld+json">'''+json.dumps(schema,ensure_ascii=False).replace('<','\\u003c')+'''</script><style>body{margin:0;background:#0d0e12;color:#f6f2ed;font:17px/1.75 system-ui,sans-serif}a{color:#f39b87}header,footer{padding:18px 24px;border-bottom:1px solid #40383c}main{max-width:800px;margin:auto;padding:55px 24px 90px}h1{font-size:clamp(35px,6vw,62px);line-height:1.1}h2{margin-top:38px}p{margin:22px 0}small{color:#c7bdb8}.cta{margin-top:45px;padding:26px;background:#25191d;border:1px solid #7e4b45;border-radius:12px}.btn{display:inline-block;background:#e55e49;color:#161217;text-decoration:none;padding:11px 20px;border-radius:8px;font-weight:800}</style></head><body><header><a href="../../index.html">RAVEN CROW · Biblioteca</a> &nbsp; / &nbsp; <a href="../../noticias.html">Coluna do Corvo</a></header><main><small>'''+esc(a.get('category','ANÁLISE'))+' · '+esc(a['date'])+''' · ANÁLISE E OPINIÃO</small><h1>'''+esc(a['title'])+'''</h1><p><strong>'''+esc(a.get('subtitle',''))+'''</strong></p><h2>O que aconteceu</h2><p>'''+esc(a.get('facts',''))+'''</p><h2>Análise do Corvo</h2><p>'''+esc(a.get('analysis',''))+'''</p><h2>Contraponto</h2><p>'''+esc(a.get('counterpoint',''))+'''</p><h2>Fontes</h2><ul>'''+sources+'''</ul><aside class="cta"><h2>Apoie o Raven Crow</h2><p>Contribua voluntariamente via Pix ou conheça os livros recomendados na Biblioteca do Corvo.</p><a class="btn" href="'''+pix+'''" data-track="pix" data-placement="artigo">Apoiar via Pix ↗</a> &nbsp; <a href="../../index.html#biblioteca" data-track="library">Ver livros ↗</a></aside></main><footer>Raven Crow · Análise opinativa baseada em fontes públicas</footer><script defer src="../../raven-analytics.js"></script></body></html>'''
    (dest/'index.html').write_text(page,encoding='utf-8')
from xml.sax.saxutils import escape
(ROOT/'public/sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join('<url><loc>'+escape(u)+'</loc></url>\n' for u in urls)+'</urlset>',encoding='utf-8')
(ROOT/'public/robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+BASE+'/sitemap.xml\n',encoding='utf-8')
# Apply the shared Raven Crow theme to regenerated article pages.
exec((ROOT/'apply-editorial-theme.py').read_text(encoding='utf-8'))
print('Generated',len(urls)-2,'article pages; SEO, CTA and analytics hooks updated')
