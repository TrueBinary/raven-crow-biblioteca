"""Site inteiro em inglês e espanhol: copia cada página em português (capa, hubs, Sobre, Termos...) com o mesmo
visual, troca os textos pelo dicionário i18n/site.json e aponta os links para as URLs do idioma (/en/about, /es/sobre).

Notícias e ensaios entram pelos blocos "en"/"es" que os agentes já escrevem; o que não tem tradução some da versão
traduzida em vez de aparecer em português. Texto novo sem tradução fica em português e é listado por --extract.
Rodar depois dos outros builders: python build-i18n-site.py [--extract]
"""
import html
import json
import re
import sys
from pathlib import Path

from news_i18n import LANGS, PAGE_SLUGS, SECTIONS, block as news_block, local_slug
from frontpage_static import inject, render_main

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
BASE = "https://ravencrow.cloud"
DICT_FILE = ROOT / "i18n" / "site.json"
# Página em português -> nome do arquivo traduzido é o slug do idioma (index fica index).
PAGES = {"index.html": "", "public/noticias.html": "noticias", "public/coluna.html": "coluna", "public/livros.html": "livros",
         "public/apoie.html": "apoie", "public/sobre.html": "sobre", "public/termos.html": "termos", "public/privacidade.html": "privacidade"}
TEXT_ATTRS = ("alt", "title", "aria-label", "placeholder", "content")
CODE_LITERAL = re.compile(r"^[a-z0-9_.:/#-]*$")  # nomes de classe, filtros, ids: nunca traduzir
SKIP_JSON_KEYS = re.compile(r'"(?:id|title|author|category|color|query)"\s*:\s*$')


def pt_url(name: str) -> str:
    return "/" + name if name else "/"


def local_url(lang: str, name: str) -> str:
    return f"/{lang}/" + (PAGE_SLUGS[lang][name] if name else "")


class Translator:
    def __init__(self, lang, words, done_news, done_essays):
        self.lang, self.words, self.missing = lang, words, set()
        self.news, self.essays = done_news, done_essays

    def word(self, raw, collect=True):
        key = " ".join(html.unescape(raw).split())
        if not key or not re.search(r"[A-Za-zÀ-ÿ]", key):
            return None
        hit = self.words.get(key)
        if hit is None and collect:
            self.missing.add(key)
        return hit

    def text(self, raw):
        hit = self.word(raw)
        if hit is None:
            return raw
        lead, trail = raw[:len(raw) - len(raw.lstrip())], raw[len(raw.rstrip()):]
        return lead + html.escape(hit, quote=False) + trail

    def link(self, url):
        """URL em português (absoluta ou relativa) -> URL do idioma; assets ficam absolutos na raiz."""
        if re.match(r"^(?:[a-z]+:|//|#|data:)", url):
            return url
        path, _, frag = url.partition("#")
        path = path if path.startswith("/") else "/" + path
        frag = "#" + frag if frag else ""
        if path == "/":
            return f"/{self.lang}/" + frag
        if path.lstrip("/") in PAGE_SLUGS[self.lang]:
            return local_url(self.lang, path.lstrip("/")) + frag
        m = re.fullmatch(r"/(noticias|coluna)/([a-z0-9-]{3,100})/?", path)
        if m:
            done = self.news if m.group(1) == "noticias" else self.essays
            if m.group(2) in done:
                local = done[m.group(2)] if isinstance(done, dict) else m.group(2)
                return f"/{self.lang}/{SECTIONS[self.lang][m.group(1)]}/{local}/" + frag
            return f"/{m.group(1)}/{m.group(2)}/" + frag
        return path + frag

    def tag(self, tag):
        def attr(m):
            name, value = m.group(1), m.group(2)
            if name in ("href", "src", "action"):
                return f'{name}="{self.link(html.unescape(value))}"'
            if name == "content" and not re.search(r'(?:name|property)="(?:description|og:title|og:description|twitter:[a-z]+)"', tag):
                return m.group(0)
            hit = self.word(value)
            return m.group(0) if hit is None else f'{name}="{html.escape(hit, quote=True)}"'
        return re.sub(r'\b(href|src|action|' + "|".join(TEXT_ATTRS) + r')="([^"]*)"', attr, tag)

    def script(self, body):
        def lit(m):
            before = body[max(0, m.start() - 40):m.start()]
            raw = m.group(2)
            if CODE_LITERAL.match(raw) or SKIP_JSON_KEYS.search(before) or "/" in raw and " " not in raw:
                return m.group(0)
            inner = raw.replace("\\" + m.group(1), m.group(1))
            hit = self.word(inner)
            if hit is None:
                return m.group(0)
            hit = inner[:len(inner) - len(inner.lstrip())] + hit + inner[len(inner.rstrip()):]
            out = json.dumps(hit, ensure_ascii=False)[1:-1]
            return m.group(1) + (out if m.group(1) == '"' else out.replace("'", "\\'").replace('\\"', '"')) + m.group(1)
        return re.sub(r"""(["'])((?:(?!\1)[^\\\n]|\\.)*)\1""", lit, body)

    def page(self, src):
        out, pos = [], 0
        for m in re.finditer(r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>|<!--.*?-->|<[^>]+>", src, re.S):
            out.append(self.text(src[pos:m.start()]) if src[pos:m.start()].strip() else src[pos:m.start()])
            piece = m.group(0)
            if piece.startswith("<script") and "application/ld+json" not in piece[:80]:
                head_end = piece.index(">") + 1
                piece = self.tag(piece[:head_end]) + self.script(piece[head_end:-9]) + "</script>"
            elif piece.startswith("<") and not piece.startswith(("<style", "<!--", "<script")):
                piece = self.tag(piece)
            out.append(piece)
            pos = m.end()
        out.append(self.text(src[pos:]))
        return "".join(out)


def alternates(name):
    links = f'<link rel="alternate" hreflang="pt-BR" href="{BASE}{pt_url(name)}">'
    links += "".join(f'<link rel="alternate" hreflang="{l}" href="{BASE}{local_url(l, name)}">' for l in LANGS)
    return links + f'<link rel="alternate" hreflang="x-default" href="{BASE}{pt_url(name)}">'


def strip_alternates(s):
    return re.sub(r'<link rel="alternate" hreflang="[^"]*" href="[^"]*">', "", s)


def dynamic_words(lang, feed, essays, featured_tail):
    """Títulos de notícias e ensaios vêm dos blocos traduzidos que os agentes escrevem."""
    words = {}
    for a in feed:
        b = news_block(a, lang)
        if b:
            words[" ".join(a.get("title", "").split())] = b["title"]
            words["Abrir matéria: " + " ".join(a.get("title", "").split())] = {"en": "Open article: ", "es": "Abrir artículo: "}[lang] + b["title"]
    for e in essays:
        b = e.get(lang)
        if isinstance(b, dict) and b.get("title"):
            for k in ("title", "subtitle", "section", "eyebrow"):
                if e.get(k) and b.get(k):
                    words[" ".join(e[k].split())] = b[k]
            if e.get("subtitle") and b.get("subtitle") and featured_tail:
                words[" ".join((e["subtitle"] + " " + featured_tail[0]).split())] = b["subtitle"] + " " + featured_tail[1]
    return words


def drop_untranslated(s, done_news, done_essays):
    s = re.sub(r'<a class="rc-col-card[^"]*" href="coluna/([a-z0-9-]+)/">.*?</a>', lambda m: m.group(0) if m.group(1) in done_essays else "", s, flags=re.S)
    return re.sub(r'<li><a href="noticias/([a-z0-9-]+)/"[^>]*>.*?</li>', lambda m: m.group(0) if m.group(1) in done_news else "", s, flags=re.S)


def build(extract=False, write=True):
    words_all = json.loads(DICT_FILE.read_text(encoding="utf-8")) if DICT_FILE.is_file() else {}
    feed = json.loads((PUBLIC / "editorial-feed.json").read_text(encoding="utf-8")).get("articles", [])
    essays = json.loads((PUBLIC / "coluna-ensaios.json").read_text(encoding="utf-8")).get("essays", [])
    books = json.loads((PUBLIC / "livros.json").read_text(encoding="utf-8"))
    images = json.loads((PUBLIC / "editorial-images.json").read_text(encoding="utf-8"))
    tail_pt = "A importância dos vínculos, do cuidado, da educação e da fé vivida em casa."
    missing = {}
    for lang in LANGS:
        static = {k: v[lang] for k, v in words_all.items() if isinstance(v, dict) and v.get(lang)}
        # id em português -> slug no idioma (news_i18n.assign_slugs)
        done_news = {a["id"]: local_slug(a, lang) for a in feed if news_block(a, lang) and (PUBLIC / lang / SECTIONS[lang]["noticias"] / local_slug(a, lang) / "index.html").is_file()}
        done_essays = {e["id"] for e in essays if (PUBLIC / lang / SECTIONS[lang]["coluna"] / e["id"] / "index.html").is_file()}
        tail = (tail_pt, static[tail_pt]) if tail_pt in static else None
        t = Translator(lang, {**static, **dynamic_words(lang, feed, essays, tail)}, done_news, done_essays)
        for src_name, name in PAGES.items():
            src = strip_alternates((ROOT / src_name).read_text(encoding="utf-8"))
            src = re.sub(r"<!-- raven-seo:start -->.*?<!-- raven-seo:end -->\n?", "", src, flags=re.S)
            src = re.sub(r'<link rel="preload" as="image" data-rc-lead[^>]*>', "", src)
            src = drop_untranslated(src, done_news, done_essays)
            if not name:  # capa: a revista em HTML é refeita no idioma depois de traduzir o resto
                src = inject(src, "")
            out = t.page(src)
            if not name:
                out = inject(out, render_main(feed, images, lang))
            out = out.replace('<html lang="pt-BR">', f'<html lang="{lang}">', 1)
            out = re.sub(r'("(?:canonical)"\s+href=|property="og:url"\s+content=)"' + re.escape(BASE) + r'/(?:index\.html)?' + re.escape(pt_url(name).lstrip("/")) + '"',
                         lambda m: m.group(1) + '"' + BASE + local_url(lang, name) + '"', out)
            meta = alternates(name) + f'<meta property="og:locale" content="{LANGS[lang]["locale"]}"><meta property="og:site_name" content="Raven Crow">'
            out = out.replace("</head>", meta + "</head>", 1)
            dest = PUBLIC / lang / ((PAGE_SLUGS[lang][name] + ".html") if name else "index.html")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if write and (not dest.is_file() or dest.read_text(encoding="utf-8") != out):
                dest.write_text(out, encoding="utf-8")
            # Português também aponta para as traduções (seletor PT·EN·ES e hreflang).
            pt_path = ROOT / src_name
            pt = pt_path.read_text(encoding="utf-8")
            pt_new = strip_alternates(pt).replace("</head>", alternates(name) + "</head>", 1)
            if write and pt_new != pt:
                pt_path.write_text(pt_new, encoding="utf-8")
        # Biblioteca: raven-books.js lê livros.json relativo à página, então /en/library busca /en/livros.json.
        tr_books = {**books, "books": [{**b, **{k: t.word(b[k]) or b[k] for k in ("description", "whyRead", "question", "cat") if b.get(k)}} for b in books["books"]]}
        if write:
            (PUBLIC / lang / "livros.json").write_text(json.dumps(tr_books, ensure_ascii=False, indent=2), encoding="utf-8")
        missing[lang] = sorted(t.missing)
    if extract:
        todo = sorted(set(missing["en"]) | set(missing["es"]))
        (ROOT / "i18n" / "missing.json").write_text(json.dumps(todo, ensure_ascii=False, indent=1), encoding="utf-8")
        print(len(todo), "textos sem tradução em i18n/missing.json")
    return missing


if __name__ == "__main__":
    miss = build("--extract" in sys.argv)
    from raven_seo import build as build_seo
    build_seo(ROOT)
    print("Site traduzido:", {l: f"{len(PAGES)} páginas, {len(m)} textos sem tradução" for l, m in miss.items()})
