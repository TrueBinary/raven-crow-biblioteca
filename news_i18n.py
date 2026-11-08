"""Translated editions of news articles: public/<lang>/noticias/<id>/ from the article's "<lang>" block, plus /<lang>/.

The news agent writes e.g. "en": {title, subtitle, facts, analysis, counterpoint, category, photo_captions} (same for "es").
Articles without a complete block get no page in that language. Photos and sources are shared with the Portuguese page.
"""
import html
import json
from pathlib import Path
from urllib.parse import urlparse

from news_photos import news_figures

REQUIRED = ("title", "facts", "analysis", "counterpoint")
LANGS = {
    "en": {"locale": "en_US", "months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
           "date": "{m} {d}, {y}", "nav": "News in English", "pill": "Analysis and opinion", "category": "ANALYSIS",
           "h": ("What <em>happened</em>", "The Crow's <em>analysis</em>", "<em>Counterpoint</em>", "<em>Sources</em>"),
           "foot": "The Crow Investigator", "edition": "English edition", "index_title": "Raven Crow — Brazil and world news in English",
           "index_desc": "Independent analysis of Brazilian and world news by Raven Crow, in English.", "index_h1": "Brazil and world <em>news</em>",
           "index_lead": "Facts, analysis and counterpoint from The Crow Investigator, translated from our Portuguese edition.",
           "soon": "English articles are coming soon.", "source": "Source"},
    "es": {"locale": "es_ES", "months": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
           "date": "{d} de {m} de {y}", "nav": "Noticias en español", "pill": "Análisis y opinión", "category": "ANÁLISIS",
           "h": ("Qué <em>pasó</em>", "Análisis del <em>Cuervo</em>", "<em>Contrapunto</em>", "<em>Fuentes</em>"),
           "foot": "El Cuervo Investigador", "edition": "Edición en español", "index_title": "Raven Crow — Noticias de Brasil y del mundo en español",
           "index_desc": "Análisis independiente de noticias de Brasil y del mundo por Raven Crow, en español.", "index_h1": "Noticias de Brasil y del <em>mundo</em>",
           "index_lead": "Hechos, análisis y contrapunto de El Cuervo Investigador, traducidos de nuestra edición en portugués.",
           "soon": "Pronto habrá artículos en español.", "source": "Fuente"},
}


def block(a: dict, lang: str):
    b = a.get(lang)
    if isinstance(b, dict) and all(isinstance(b.get(k), str) and b[k].strip() for k in REQUIRED):
        return b
    return None


def langs_of(a: dict) -> list:
    return [l for l in LANGS if block(a, l)]


def fmt_date(d: str, lang: str) -> str:
    y, m, dd = str(d).split("-")[:3]
    L = LANGS[lang]
    return L["date"].format(m=L["months"][int(m) - 1], d=int(dd), y=y)


def hreflang(pt_url: str, alts: dict) -> str:
    """alts: {lang: url} for the translated versions that exist."""
    out = f'<link rel="alternate" hreflang="pt-BR" href="{pt_url}">'
    out += "".join(f'<link rel="alternate" hreflang="{l}" href="{u}">' for l, u in alts.items())
    return out + f'<link rel="alternate" hreflang="x-default" href="{pt_url}">'


def _esc(v):
    return html.escape(str(v or ""), quote=True)


def _head(lang, title, desc, url, alternates, css, extra=""):
    return ('<!doctype html><html lang="' + lang + '"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="theme-color" content="#0d0e12"><title>' + _esc(title) + '</title><meta name="description" content="' + _esc(desc[:155]) + '">'
            '<link rel="canonical" href="' + url + '">' + alternates + '<meta property="og:title" content="' + _esc(title) + '">'
            '<meta property="og:description" content="' + _esc(desc) + '"><meta property="og:url" content="' + url + '"><meta property="og:locale" content="' + LANGS[lang]["locale"] + '">'
            + extra + '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@800;900&family=DM+Sans:wght@400;500;600;700;800&display=swap">'
            '<style>' + css + '</style></head>')


def _top(lang, prefix, pt_href):
    return ('<header class="rc-top"><div class="rc-line"><a class="rc-brand" href="' + prefix + lang + '/"><i aria-hidden="true"></i>RAVEN CROW</a>'
            '<nav aria-label="Sections"><a href="' + prefix + lang + '/">' + LANGS[lang]["nav"] + '</a><a href="' + pt_href + '" hreflang="pt-BR">Português</a></nav></div>'
            '<img class="rc-logo" src="' + prefix + 'raven-logo.webp" alt="" width="56" height="56"></header>')


def url_of(base: str, lang: str, slug: str) -> str:
    return f"{base}/{lang}/noticias/{slug}/"


def render_article(root: Path, a: dict, lang: str, updated: str, credits: dict, css: str, base: str, title_html) -> str:
    """Write public/<lang>/noticias/<id>/index.html and return its URL."""
    b, slug, L = block(a, lang), a["id"], LANGS[lang]
    url, pt_url = url_of(base, lang, slug), f"{base}/noticias/{slug}/"
    caps = b.get("photo_captions") if isinstance(b.get("photo_captions"), dict) else {}
    local = dict(credits)
    for n, key in ((1, slug), (2, f"{slug}--2"), (3, f"{slug}--3")):
        if key in local:
            local[key] = {**local[key], "caption": str(caps.get(str(n)) or "")}
    figs = news_figures(slug, local, root / "public", b["title"], prefix="../../../")
    sources = "".join('<li><a rel="noopener noreferrer" target="_blank" href="' + _esc(s["url"]) + '">' + _esc(s.get("name", L["source"])) + "</a></li>"
                      for s in a.get("sources", []) if urlparse(s.get("url", "")).scheme == "https")
    schema = {"@context": "https://schema.org", "@type": "Article", "headline": b["title"], "description": b.get("subtitle", ""),
              "inLanguage": lang, "datePublished": a["date"], "dateModified": updated, "author": {"@type": "Organization", "name": "Raven Crow"},
              "publisher": {"@type": "Organization", "name": "Raven Crow"}, "mainEntityOfPage": url, "isAccessibleForFree": True}
    ld = '<meta property="og:type" content="article"><script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c") + "</script>"
    alts = {l: url_of(base, l, slug) for l in langs_of(a)}
    h = L["h"]
    page = (_head(lang, b["title"] + " | Raven Crow", b.get("subtitle", ""), url, hreflang(pt_url, alts), css, ld)
            + '<body class="rc-news">' + _top(lang, "../../../", "../../../noticias/" + slug + "/")
            + '<main><span class="rc-pill">' + _esc(b.get("category") or L["category"]) + " / " + L["pill"] + "</span><h1>" + title_html(b["title"]) + "</h1>"
            + "<p><strong>" + _esc(b.get("subtitle", "")) + "</strong></p>" + figs["style"] + figs["top"]
            + "<h2>" + h[0] + "</h2><p>" + _esc(b["facts"]) + "</p>" + figs["fatos"]
            + "<h2>" + h[1] + "</h2><p>" + _esc(b["analysis"]) + "</p>" + figs["analise"]
            + "<h2>" + h[2] + "</h2><p>" + _esc(b["counterpoint"]) + "</p>" + figs["contraponto"]
            + "<h2>" + h[3] + "</h2><ul>" + sources + "</ul>"
            + '<p><a href="../../../noticias/' + slug + '/" hreflang="pt-BR">Leia em português →</a></p></main>'
            + '<footer class="rc-foot"><span>' + L["foot"] + " / " + fmt_date(a["date"], lang) + "</span><b>Raven Crow</b></footer>"
            + '<script defer src="../../../raven-analytics.js"></script></body></html>')
    dest = root / "public" / lang / "noticias" / slug
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(page, encoding="utf-8")
    return url


def render_index(root: Path, lang: str, items: list, css: str, base: str) -> str:
    """Write public/<lang>/index.html listing the articles in that language (newest first) and return its URL."""
    L, url = LANGS[lang], f"{base}/{lang}/"
    rows = "".join('<li><a href="noticias/' + _esc(a["id"]) + '/"><strong>' + _esc(block(a, lang)["title"]) + "</strong></a><br><small>"
                   + fmt_date(a["date"], lang) + " · " + _esc(block(a, lang).get("subtitle", "")) + "</small></li>"
                   for a in sorted(items, key=lambda x: x.get("date", ""), reverse=True))
    alts = {l: f"{base}/{l}/" for l in LANGS}
    page = (_head(lang, L["index_title"], L["index_desc"], url, hreflang(base + "/", alts), css)
            + '<body class="rc-news">' + _top(lang, "../", "../index.html")
            + '<main><span class="rc-pill">Raven Crow / ' + L["edition"] + "</span><h1>" + L["index_h1"] + "</h1>"
            + "<p><strong>" + L["index_lead"] + "</strong></p>"
            + "<ul>" + (rows or "<li>" + L["soon"] + "</li>") + "</ul></main>"
            + '<footer class="rc-foot"><span>Raven Crow / ' + L["edition"] + "</span><b>Raven Crow</b></footer>"
            + '<script defer src="../raven-analytics.js"></script></body></html>')
    (root / "public" / lang).mkdir(parents=True, exist_ok=True)
    (root / "public" / lang / "index.html").write_text(page, encoding="utf-8")
    return url
