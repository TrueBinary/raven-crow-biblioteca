"""Build a durable Raven Crow opinion section from separately maintained essay data.

Existing archived articles remain in editorial-feed.json, rendered by raven-column.js.
"""
from pathlib import Path
from html import escape
import json
import re
from column_photos import photo_figure
from news_i18n import hreflang

# Translated essays: "en"/"es" block {title, subtitle, eyebrow, section, paragraphs:[...], photo_caption} -> /<lang>/coluna/<id>/.
COL_LANGS={
 "en":{"tag":"Opinion","crumb":"The Crow's Column","sources":"Sources and further reading","note":"This text is an interpretive essay. The sources listed let you consult the original works and documents.","back":"← Read in Portuguese","support":"Support the project ↗","by":"The Crow Investigator","foot":"© Raven Crow · Editorial opinion"},
 "es":{"tag":"Opinión","crumb":"La Columna del Cuervo","sources":"Fuentes y lecturas","note":"Este texto es un ensayo de interpretación. Las fuentes citadas permiten consultar las obras y documentos originales.","back":"← Leer en portugués","support":"Apoya el proyecto ↗","by":"El Cuervo Investigador","foot":"© Raven Crow · Opinión editorial"},
}
def essay_block(essay,lang):
    b=essay.get(lang)
    ok=isinstance(b,dict) and isinstance(b.get("title"),str) and b["title"].strip() and isinstance(b.get("paragraphs"),list) and b["paragraphs"] and all(isinstance(p,str) and p.strip() for p in b["paragraphs"])
    return b if ok else None

ROOT=Path(__file__).resolve().parent
PUBLIC=ROOT/"public"
BASE="https://ravencrow.cloud"
ESSAYS=json.loads((PUBLIC/"coluna-ensaios.json").read_text(encoding="utf-8"))["essays"]
try:PHOTO_CREDITS=json.loads((PUBLIC/"editorial-photo-credits.json").read_text(encoding="utf-8"))
except (FileNotFoundError,ValueError):PHOTO_CREDITS={}
source=(PUBLIC/"coluna.html").read_text(encoding="utf-8")
match=re.search(r'<header class="rc-global-header">.*?</header>',source,re.S)
if not match:raise ValueError("Existing shared Raven Crow header missing")
HEADER=match.group(0)

def h(value):
    return escape(str(value),quote=True)

def meta(title,summary,canonical,article=False,base=False):
    base_tag='<base href="../../">' if base else ""
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0b0c0f">
<title>{h(title)} | Raven Crow</title><meta name="description" content="{h(summary[:155])}">
<link rel="canonical" href="{h(canonical)}"><meta property="og:type" content="{'article' if article else 'website'}">
<meta property="og:title" content="{h(title)}"><meta property="og:description" content="{h(summary)}">
{base_tag}<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=DM+Sans:wght@400;500;600;700;800&display=swap">
<link rel="stylesheet" href="raven-navigation.css"><link rel="stylesheet" href="raven-column.css">
<script defer src="raven-navigation.js"></script></head>'''

def essay_card(a,klass=""):
    slug=h(a["id"])
    return (f'<a class="rc-col-card {klass}" href="coluna/{slug}/">'
            f'<span class="rc-col-card-category">{h(a["section"])} · Opinião</span>'
            f'<h3>{h(a["title"])}</h3><p>{h(a["subtitle"])}</p>'
            f'<span class="rc-col-read">Ler reflexão <span aria-hidden="true">↗</span></span></a>')

assert len(ESSAYS)>=3
ids=set()
for essay in ESSAYS:
    slug=essay["id"]
    if not re.fullmatch(r"[a-z0-9-]{6,100}",slug) or slug in ids:
        raise ValueError("Invalid/duplicate essay slug")
    if len(essay.get("paragraphs",[]))<4 or not essay.get("sources"):
        raise ValueError("Every opinion essay needs content and sources")
    ids.add(slug)

featured=next(a for a in ESSAYS if a["section"]=="Fé e família")
others=[a for a in ESSAYS if a["id"]!=featured["id"]]
# The opinion hub is also a gateway to the complete existing news-analysis archive.
hub=f'''{meta("Coluna do Corvo — Política, Filosofia, Fé e Família","Ensaios e opiniões sobre política, filosofia, fé e família, além das análises já publicadas pelo Raven Crow.",BASE+"/coluna.html")}
<body class="rc-subpage rc-column">{HEADER}
<main id="main-content" class="rc-col-shell">
<section class="rc-col-hero" aria-labelledby="column-heading">
  <p class="rc-col-eyebrow"><span></span> O CORVO INVESTIGADOR / ENSAIOS E REFLEXÕES</p>
  <h1 id="column-heading">COLUNA <em>DO CORVO.</em></h1>
  <p class="rc-col-hero-lead">Política, filosofia e vida cristã. Ideias discutidas com argumentos, fontes e espaço para o contraditório.</p>
  <div class="rc-col-navlinks" aria-label="Assuntos da coluna">
    <a href="#politica">Política e sociedade</a><a href="#filosofia">Filosofia e ideias</a>
    <a href="#familia">Fé e família</a><a href="#arquivo">Arquivo de análises</a>
  </div>
</section>
<section id="familia" class="rc-col-feature" aria-labelledby="familia-heading">
  <div class="rc-col-feature-mark"><span>03</span><strong>FÉ<br>FAMÍLIA</strong></div>
  <div class="rc-col-feature-copy">
    <p class="rc-col-overline">FÉ E FAMÍLIA / REFLEXÃO CRISTÃ</p>
    <h2 id="familia-heading">{h(featured["title"])}</h2>
    <p>{h(featured["subtitle"])} A importância dos vínculos, do cuidado, da educação e da fé vivida em casa.</p>
    <a class="rc-col-cta" href="coluna/{h(featured['id'])}/">Ler reflexão completa <span aria-hidden="true">↗</span></a>
  </div>
</section>
<div class="rc-col-track-grid">
<section id="politica" class="rc-col-track" aria-labelledby="politica-heading">
  <div class="rc-col-track-heading"><span class="rc-col-count">01</span><div><p>OPINIÃO POLÍTICA</p><h2 id="politica-heading">Política e sociedade</h2></div></div>
  <p class="rc-col-track-intro">Poder, representação, responsabilidade e limites institucionais.</p>
  {''.join(essay_card(a) for a in others if a["section"]=="Política e sociedade")}
</section>
<section id="filosofia" class="rc-col-track" aria-labelledby="filosofia-heading">
  <div class="rc-col-track-heading"><span class="rc-col-count">02</span><div><p>QUESTÕES PERENES</p><h2 id="filosofia-heading">Filosofia e ideias</h2></div></div>
  <p class="rc-col-track-intro">Direito natural, consciência moral, liberdade e o problema do justo.</p>
  {''.join(essay_card(a) for a in others if a["section"]=="Filosofia e ideias")}
</section>
</div>
<section id="arquivo" class="rc-col-archive" aria-labelledby="archive-heading">
  <div class="rc-col-archive-head"><div><p class="rc-col-overline">MATÉRIAS QUE JÁ PUBLICAMOS</p><h2 id="archive-heading">Arquivo de análises</h2></div><a href="noticias.html">Ver todas as notícias <span aria-hidden="true">↗</span></a></div>
  <p class="rc-col-archive-desc">Textos publicados anteriormente pelo Corvo Investigador, mantidos no acervo com suas datas, fontes e contrapontos.</p>
  <div id="rc-col-archive-list" class="rc-col-archive-list" aria-live="polite"><p class="rc-col-loading">Carregando análises anteriores...</p></div>
</section>
<section class="rc-col-closing" aria-label="Linha editorial">
 <span class="rc-col-closer-icon" aria-hidden="true">✦</span>
 <div><h2>Convicção não dispensa argumento.</h2><p>Os ensaios expressam interpretações editoriais. Fatos, documentos e posições contrárias devem permanecer identificáveis. Os próximos textos poderão ampliar esta seção sem apagar o acervo anterior.</p></div>
 <a href="sobre.html">Conheça o projeto <span aria-hidden="true">↗</span></a>
</section>
</main>
<footer class="rc-col-footer"><div>© Raven Crow · O Corvo Investigador</div><div><a href="noticias.html">Notícias</a> · <a href="apoie.html">Apoie</a> · <a href="index.html">Início</a></div></footer>
<script defer src="raven-column.js"></script><script defer src="raven-analytics.js"></script>
</body></html>'''
(PUBLIC/"coluna.html").write_text(hub,encoding="utf-8")

for essay in ESSAYS:
    slug=essay["id"]
    url=f"{BASE}/coluna/{slug}/"
    paragraphs="".join(f"<p>{h(p)}</p>" for p in essay["paragraphs"])
    sources="".join(f'<li><a rel="noopener noreferrer" target="_blank" href="{h(s["url"])}">{h(s["title"])}</a></li>' for s in essay["sources"] if s["url"].startswith("https://"))
    article=f'''{meta(essay["title"],essay["subtitle"],url,article=True,base=True)}
<body class="rc-subpage rc-column rc-column-article">{HEADER}
<main class="rc-col-story" id="main-content">
 <nav class="rc-col-breadcrumb" aria-label="Localização"><a href="coluna.html">Coluna do Corvo</a> <span aria-hidden="true">/</span> {h(essay["section"])}</nav>
 <header class="rc-col-story-header">
  <span class="rc-col-story-tag">{h(essay["eyebrow"])} · Opinião</span>
  <h1>{h(essay["title"])}</h1><p class="rc-col-story-dek">{h(essay["subtitle"])}</p>
  <p class="rc-col-story-byline">O Corvo Investigador · Raven Crow · {h(essay["date"][8:10])}/{h(essay["date"][5:7])}/{h(essay["date"][:4])}</p>
 </header>
 {photo_figure(slug,PHOTO_CREDITS,PUBLIC,essay["title"])}
 <article class="rc-col-story-body">{paragraphs}</article>
 <section class="rc-col-sources" aria-labelledby="sources-heading"><h2 id="sources-heading">Fontes e leituras</h2><ul>{sources}</ul><p>Este texto é um ensaio de interpretação. As fontes citadas permitem consultar as obras e documentos originais.</p></section>
 <div class="rc-col-story-back"><a href="coluna.html">← Voltar à Coluna do Corvo</a><a href="apoie.html">Apoie o projeto ↗</a></div>
</main><footer class="rc-col-footer"><div>© Raven Crow · Opinião editorial</div><div><a href="coluna.html">Outros ensaios</a> · <a href="index.html">Início</a></div></footer>
<script defer src="raven-analytics.js"></script></body></html>'''
    tr={l:f"{BASE}/{l}/coluna/{slug}/" for l in COL_LANGS if essay_block(essay,l)}
    canon=f'<link rel="canonical" href="{h(url)}">'
    if tr:article=article.replace(canon,canon+hreflang(url,tr),1)
    target=PUBLIC/"coluna"/slug
    target.mkdir(parents=True,exist_ok=True)
    (target/"index.html").write_text(article,encoding="utf-8")
    for lang,lurl in tr.items():
        b,L=essay_block(essay,lang),COL_LANGS[lang]
        credits=dict(PHOTO_CREDITS)
        if slug in credits:credits[slug]={**credits[slug],"caption":str(b.get("photo_caption") or "")}
        paras="".join(f"<p>{h(p)}</p>" for p in b["paragraphs"])
        page=f'''{meta(b["title"],b.get("subtitle",""),lurl,article=True,base=True)}
<body class="rc-subpage rc-column rc-column-article">{HEADER}
<main class="rc-col-story" id="main-content">
 <nav class="rc-col-breadcrumb" aria-label="Breadcrumb"><a href="coluna/{slug}/" hreflang="pt-BR">{L["crumb"]}</a> <span aria-hidden="true">/</span> {h(b.get("section") or essay["section"])}</nav>
 <header class="rc-col-story-header">
  <span class="rc-col-story-tag">{h(b.get("eyebrow") or essay["eyebrow"])} · {L["tag"]}</span>
  <h1>{h(b["title"])}</h1><p class="rc-col-story-dek">{h(b.get("subtitle",""))}</p>
  <p class="rc-col-story-byline">{L["by"]} · Raven Crow · {h(essay["date"])}</p>
 </header>
 {photo_figure(slug,credits,PUBLIC,b["title"])}
 <article class="rc-col-story-body">{paras}</article>
 <section class="rc-col-sources" aria-labelledby="sources-heading"><h2 id="sources-heading">{L["sources"]}</h2><ul>{sources}</ul><p>{L["note"]}</p></section>
 <div class="rc-col-story-back"><a href="coluna/{slug}/" hreflang="pt-BR">{L["back"]}</a><a href="apoie.html">{L["support"]}</a></div>
</main><footer class="rc-col-footer"><div>{L["foot"]}</div><div><a href="{lang}/">Raven Crow · {lang.upper()}</a> · <a href="index.html">Raven Crow</a></div></footer>
<script defer src="raven-analytics.js"></script></body></html>'''
        page=page.replace('<html lang="pt-BR">',f'<html lang="{lang}">',1).replace('<base href="../../">','<base href="../../../">',1)
        image=f"{BASE}/editorial/photos/{slug}.jpg" if (PUBLIC/"editorial"/"photos"/f"{slug}.jpg").is_file() else None
        schema={"@context":"https://schema.org","@type":"Article","headline":b["title"],"description":b.get("subtitle",""),"genre":L["tag"],
                "inLanguage":lang,"datePublished":essay["date"],"author":{"@type":"Organization","name":"Raven Crow"},
                "publisher":{"@type":"Organization","name":"Raven Crow"},"mainEntityOfPage":lurl,"isAccessibleForFree":True,**({"image":image} if image else {})}
        extra=(f'<meta property="og:image" content="{image}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{image}">' if image else "")
        extra+='<script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False).replace("<","\u003c")+"</script>"
        page=page.replace(canon.replace(h(url),h(lurl)),canon.replace(h(url),h(lurl))+hreflang(url,tr)+extra,1)
        d=PUBLIC/lang/"coluna"/slug
        d.mkdir(parents=True,exist_ok=True)
        (d/"index.html").write_text(page,encoding="utf-8")
from raven_seo import build as build_seo
build_seo(ROOT)
print("Generated",len(ESSAYS),"Raven Crow essays and an opinion archive hub")
