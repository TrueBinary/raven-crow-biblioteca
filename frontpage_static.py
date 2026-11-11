"""Capa em HTML pronto: destaque + últimas notícias saem do build, não do JavaScript.

Antes a capa chegava com uma lista de links e o raven-frontpage.js trocava tudo pela revista depois do fetch do feed,
empurrando a página inteira (CLS 0,8 no PageSpeed) e atrasando a foto do destaque (LCP). Agora o HTML já vem igual ao
que o script desenharia, com as fotos WebP do tamanho certo; o script só completa a coluna lateral.
Mesma marcação de raven-frontpage.js: mudou um, mude o outro.
"""
import re
from html import escape

from news_i18n import SECTIONS, block

T = {
    "pt": {"img": "Imagem ilustrativa: ", "news": "Notícias", "lead": "Confira a análise completa.", "min": " min de leitura", "file": "Foto ilustrativa de arquivo",
           "latest": "ÚLTIMAS NOTÍCIAS", "analysis": "Análise", "more": "Leia a matéria completa.", "credits": "Créditos e licenças das fotografias"},
    "en": {"img": "Illustrative image: ", "news": "News", "lead": "Read the full analysis.", "min": " min read", "file": "Illustrative file photo",
           "latest": "LATEST NEWS", "analysis": "Analysis", "more": "Read the full story.", "credits": "Photo credits and licenses"},
    "es": {"img": "Imagen ilustrativa: ", "news": "Noticias", "lead": "Lee el análisis completo.", "min": " min de lectura", "file": "Foto ilustrativa de archivo",
           "latest": "ÚLTIMAS NOTICIAS", "analysis": "Análisis", "more": "Lee la nota completa.", "credits": "Créditos y licencias de las fotografías"},
}
HERO_SIZES = "(max-width: 900px) 100vw, 900px"
THUMB_SIZES = "(max-width: 600px) 40vw, 260px"


def _story(a: dict, lang: str):
    if lang == "pt":
        return a
    b = block(a, lang)
    return {**a, "title": b["title"], "subtitle": b.get("subtitle", ""), "category": b.get("category", ""),
            "facts": b["facts"], "analysis": b["analysis"], "counterpoint": b["counterpoint"]} if b else None


def _minutes(a: dict) -> int:
    words = len(" ".join([a.get("facts") or "", a.get("analysis") or "", a.get("counterpoint") or ""]).split())
    return max(2, -(-words // 210))


def _date(d: str, lang: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d or ""):
        return "Raven Crow"
    y, m, dd = d.split("-")
    return f"{m}/{dd}/{y}" if lang == "en" else f"{dd}/{m}/{y}"


def _img(a: dict, images: dict, cls: str, alt: str, sizes: str, eager: bool) -> str:
    v = images.get("photoVariants", {}).get(a["id"])
    photo = images.get("photos", {}).get(a["id"], "")
    cover = images.get("covers", {}).get(a["id"], "")
    if v:
        srcset = ", ".join("/" + part.strip() for part in v["srcset"].split(","))
        attrs = f'src="/{escape(v["src"])}" srcset="{escape(srcset)}" sizes="{sizes}" width="{v["width"]}" height="{v["height"]}"'
    elif re.fullmatch(r"editorial/photos/[a-z0-9-]+\.jpg", photo):
        attrs = f'src="/{photo}"'
    elif re.fullmatch(r"editorial/covers/[a-z0-9-]+\.svg", cover):
        attrs = f'src="/{cover}"'
    else:
        return ""
    load = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    return f'<img class="{cls}" {attrs} alt="{escape(alt, quote=True)}" {load} decoding="async">'


def render_main(articles: list, images: dict, lang: str) -> str:
    """Conteúdo de <div class="rc-mag-main"> da capa no idioma (destaque + 5 matérias)."""
    t = T[lang]
    path = "/noticias/" if lang == "pt" else f"/{lang}/{SECTIONS[lang]['noticias']}/"
    stories = [s for a in articles if re.fullmatch(r"[a-z0-9-]{3,100}", str(a.get("id", ""))) and (s := _story(a, lang))][:6]
    if not stories:
        return ""
    lead, e = stories[0], escape
    pic = _img(lead, images, "rc-mag-hero-image", t["img"] + lead["title"], HERO_SIZES, True)
    out = (f'<a class="rc-mag-hero" href="{path}{lead["id"]}/" id="{lead["id"]}">{pic}<div class="rc-mag-hero-content">'
           f'<span class="rc-mag-tag">{e(lead.get("category") or t["news"])}</span><h2>{e(lead["title"])}</h2><p>{e(lead.get("subtitle") or t["lead"])}</p>'
           f'<span class="rc-mag-meta">{_date(lead.get("date", ""), lang)}  ·  {_minutes(lead)}{t["min"]}{"  ·  " + t["file"] if pic else ""}</span></div></a>'
           f'<h2 class="rc-mag-section-title">{t["latest"]}</h2><div class="rc-mag-list">')
    for a in stories[1:]:
        pic = _img(a, images, "rc-mag-item-image", t["img"] + a["title"], THUMB_SIZES, False)
        tile = (f'<div class="rc-mag-thumbnail">{pic}</div>' if pic else
                '<div class="rc-mag-thumbnail rc-mag-thumbnail-empty"><img class="rc-mag-placeholder" src="/raven-logo.webp" alt="" loading="lazy" decoding="async"></div>')
        out += (f'<a class="rc-mag-item" href="{path}{a["id"]}/" id="{a["id"]}">{tile}<div class="rc-mag-item-body">'
                f'<span class="rc-mag-tag">{e(a.get("category") or t["analysis"])}</span><h3>{e(a["title"])}</h3><p>{e(a.get("subtitle") or t["more"])}</p>'
                f'<span class="rc-mag-meta">{_date(a.get("date", ""), lang)}  ·  {_minutes(a)}{t["min"]}</span></div></a>')
    out += "</div>"
    if images.get("photos"):
        out += f'<a class="rc-mag-photo-credits" href="/creditos-fotos">{t["credits"]}</a>'
    return out


CSS = ("raven-editorial.css", "raven-unified.css", "raven-navigation.css")
FONTS = [("Barlow Condensed", w, f"barlow-condensed-{w}") for w in (600, 700, 800, 900)] + [("DM Sans", "400 700", "dm-sans")]
# O que inline_head() troca: links do Google Fonts, os 3 CSS da capa e o bloco que ela mesma escreveu antes.
HEAD = re.compile(r'<link rel="preconnect" href="https://fonts\.g[^>]*>\s*|<link href="https://fonts\.googleapis\.com/[^>]*>\s*'
                  r'|<link rel="stylesheet" href="/?(?:' + "|".join(re.escape(c) for c in CSS) + r')">\s*'
                  r'|<link rel="preload" as="font"[^>]*>\s*|<style data-inline="[^"]*">.*?</style>\s*', re.S)


def inline_head(page: str, public) -> str:
    """CSS da capa e fontes próprias dentro do HTML: o primeiro desenho não espera 4 idas à rede (FCP no PageSpeed).

    Lê os .css a cada build, então mudar raven-unified.css continua valendo na capa.
    """
    css = "".join(f"@font-face{{font-family:'{f}';font-style:normal;font-weight:{w};font-display:swap;src:url(/fonts/{n}.woff2) format('woff2')}}"
                  for f, w, n in FONTS)
    css += "\n".join((public / c).read_text(encoding="utf-8") for c in CSS)
    block = ('<link rel="preload" as="font" type="font/woff2" href="/fonts/barlow-condensed-900.woff2" crossorigin>\n'
             '<link rel="preload" as="font" type="font/woff2" href="/fonts/dm-sans.woff2" crossorigin>\n'
             f'<style data-inline="{" ".join(CSS)}">{css}</style>\n')
    first = []
    out = HEAD.sub(lambda m: "" if first else first.append(1) or block, page)
    if not first:
        raise RuntimeError("Capa sem os links de CSS/fontes esperados")
    return out


MAIN = re.compile(r'(<div class="rc-mag-main"(?: data-ssr="1")?>).*?(</div>\s*<div class="rc-mag-side">)', re.S)


def inject(page: str, html: str) -> str:
    """Troca o conteúdo da .rc-mag-main da capa (a lista antiga de links ou a revista anterior)."""
    new, n = MAIN.subn(lambda m: '<div class="rc-mag-main" data-ssr="1">' + html + m.group(2), page, count=1)
    if n != 1:
        raise RuntimeError("Capa sem .rc-mag-main seguida de .rc-mag-side")
    return new
