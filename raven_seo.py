"""Add structured data and maintain a canonical sitemap for published Raven Crow pages.

Static, offline and idempotent. Never changes editorial text, styles, ads or media.
Safe to call after any of the existing site builders.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from html import escape as html_escape
import json
from pathlib import Path
import re
from xml.sax.saxutils import escape as xml_escape

BASE = "https://ravencrow.cloud"
SLUG = re.compile(r"[a-z0-9-]{3,100}\Z")
MARKED = re.compile(r"\s*<!-- raven-seo:start -->.*?<!-- raven-seo:end -->\s*", re.S)
JSONLD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def _read_json(file: Path, default):
    if not file.exists():
        return default
    return json.loads(file.read_text(encoding="utf-8"))


def _date(value):
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def _article_date(item):
    return _date(item.get("updatedAt")) or _date(item.get("date"))


def _write_if_changed(path: Path, content: str):
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _published(path: Path, canonical: str, *, allow_missing=False):
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    if re.search(r'<link\s+rel="canonical"\s+href="' + re.escape(canonical) + r'"', text):
        return True
    # Only pages already present in the approved editorial JSON may ask
    # for this repair. Never overwrite a conflicting canonical.
    if not allow_missing or re.search(r'<link[^>]*rel=["\']canonical["\']', text, re.I):
        return False
    if not all(marker in text for marker in ("<head", "</head>", "<title>", "<body")):
        return False
    text = text.replace("</head>",
                        '<link rel="canonical" href="' + html_escape(canonical, quote=True) + '"></head>',
                        1)
    _write_if_changed(path, text)
    return True


def _news_data(pub: Path):
    # Main edition takes precedence over archives; old IDs remain discoverable.
    news = {}
    sources = [pub / "noticias.json"]
    sources.extend(sorted((pub / "arquivo").glob("noticias-*.json"), reverse=True))
    for file in sources:
        for article in _read_json(file, {}).get("articles", []):
            slug = str(article.get("id", ""))
            if SLUG.fullmatch(slug):
                news.setdefault(slug, article)
    # The editorial feed may be ahead of archived sources; never add its
    # entries to the sitemap unless an actual canonical HTML page exists.
    for article in _read_json(pub / "editorial-feed.json", {}).get("articles", []):
        slug = str(article.get("id", ""))
        if SLUG.fullmatch(slug):
            news.setdefault(slug, article)
    return news


def _org():
    return {
        "@type": "Organization", "@id": BASE + "/#organization",
        "name": "Raven Crow", "url": BASE + "/",
        "logo": BASE + "/raven-logo.webp",
        "sameAs": [
            "https://www.instagram.com/ravencrowcc/",
            "https://www.youtube.com/channel/UC7QOwGdezKSy8NiaIalE9-w",
        ],
    }


def _crumbs(section: str, name: str, url: str):
    return {
        "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Início", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": section,
             "item": BASE + ("/noticias.html" if section == "Notícias" else "/coluna.html")},
            {"@type": "ListItem", "position": 3, "name": name, "item": url},
        ],
    }


def _metadata(path: Path, graph: list, *, published=None, modified=None, image=None):
    page = path.read_text(encoding="utf-8")
    # Replace only a legacy Article schema. Preserve unrelated schema
    # (for example a separately authored FAQ or custom data) on every rerun.
    already_marked = MARKED.search(page) is not None
    page = MARKED.sub("", page)
    if published and not already_marked:
        def remove_legacy_article(match):
            try:
                content = json.loads(match.group(1))
            except (ValueError, TypeError):
                return match.group(0)
            if isinstance(content, dict) and content.get("@type") in {
                "Article", "NewsArticle", "BlogPosting"
            }:
                return ""
            return match.group(0)
        page = JSONLD.sub(remove_legacy_article, page)
    head = [
        "<!-- raven-seo:start -->",
        '<meta property="og:locale" content="pt_BR">',
        '<meta property="og:site_name" content="Raven Crow">',
        '<meta name="twitter:card" content="' + ("summary_large_image" if image else "summary") + '">',
    ]
    if published:
        head.append('<meta property="article:published_time" content="' + html_escape(published) + '">')
        head.append('<meta property="article:modified_time" content="' + html_escape(modified or published) + '">')
    if image:
        head.append('<meta property="og:image" content="' + html_escape(image, quote=True) + '">')
        head.append('<meta name="twitter:image" content="' + html_escape(image, quote=True) + '">')
    payload = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    head.append('<script type="application/ld+json">' + payload.replace("<", r"\u003c") + '</script>')
    head.append("<!-- raven-seo:end -->")
    if "</head>" not in page:
        raise ValueError(f"Missing HTML head: {path}")
    page = page.replace("</head>", "\n" + "\n".join(head) + "\n</head>", 1)
    _write_if_changed(path, page)


def build(root: Path, today: date | None = None) -> dict:
    root = Path(root)
    pub = root / "public"
    news = _news_data(pub)
    essays = {
        x["id"]: x for x in _read_json(pub / "coluna-ensaios.json", {}).get("essays", [])
        if SLUG.fullmatch(str(x.get("id", "")))
    }
    entries = [(BASE + "/", None)]
    for name in ("noticias", "coluna", "livros", "apoie", "sobre"):
        url = BASE + "/" + name + ".html"
        if _published(pub / (name + ".html"), url):
            entries.append((url, None))

    linked_news = []
    recent_news = []
    for slug, item in sorted(news.items(), key=lambda kv: (kv[1].get("date", ""), kv[0]), reverse=True):
        url = BASE + "/noticias/" + slug + "/"
        file = pub / "noticias" / slug / "index.html"
        published = _date(item.get("date"))
        if not published or not _published(file, url, allow_missing=True):
            continue
        modified = _article_date(item) or published
        photo = pub / "editorial" / "photos" / (slug + ".jpg")
        image = BASE + "/editorial/photos/" + slug + ".jpg" if photo.is_file() else None
        citations = [
            source["url"] for source in item.get("sources", [])
            if isinstance(source, dict) and str(source.get("url", "")).startswith("https://")
        ]
        article = {
            "@type": "Article", "@id": url + "#article",
            "headline": item.get("title", ""), "description": item.get("subtitle", ""),
            "datePublished": published, "dateModified": modified, "inLanguage": "pt-BR",
            "articleSection": item.get("category", "Análise"),
            "author": {"@id": BASE + "/#organization"},
            "publisher": {"@id": BASE + "/#organization"},
            "mainEntityOfPage": {"@type": "WebPage", "@id": url},
            "isAccessibleForFree": True,
        }
        if image:
            article["image"] = image
        if citations:
            article["citation"] = citations
        _metadata(file, [article, _crumbs("Notícias", item.get("title", ""), url)],
                  published=published, modified=modified, image=image)
        entries.append((url, modified))
        linked_news.append((url, item.get("title", "")))
        recent_news.append((url, item.get("title", ""), published))

    for slug, item in sorted(essays.items()):
        url = BASE + "/coluna/" + slug + "/"
        file = pub / "coluna" / slug / "index.html"
        published = _date(item.get("date"))
        if not published or not _published(file, url, allow_missing=True):
            continue
        article = {
            "@type": "Article", "@id": url + "#article",
            "headline": item.get("title", ""), "description": item.get("subtitle", ""),
            "genre": "Opinião", "articleSection": item.get("section", "Coluna"),
            "datePublished": published, "dateModified": _article_date(item) or published,
            "inLanguage": "pt-BR", "author": {"@id": BASE + "/#organization"},
            "publisher": {"@id": BASE + "/#organization"},
            "mainEntityOfPage": {"@type": "WebPage", "@id": url},
            "isAccessibleForFree": True,
        }
        photo = pub / "editorial" / "photos" / (slug + ".jpg")
        image = BASE + "/editorial/photos/" + slug + ".jpg" if photo.is_file() else None
        if image:
            article["image"] = image
        _metadata(file, [article, _crumbs("Coluna", item.get("title", ""), url)],
                  published=published, modified=article["dateModified"], image=image)
        entries.append((url, article["dateModified"]))

    home = root / "index.html"
    if _published(home, BASE + "/"):
        _metadata(home, [_org(), {
            "@type": "WebSite", "@id": BASE + "/#website", "name": "Raven Crow",
            "url": BASE + "/", "inLanguage": "pt-BR",
            "publisher": {"@id": BASE + "/#organization"},
        }])
    hubs = {
        "noticias": ("CollectionPage", {
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": i, "name": title, "url": url}
                for i, (url, title) in enumerate(linked_news, 1)
            ],
        }),
        "coluna": ("CollectionPage", None),
        "livros": ("CollectionPage", None),
        "sobre": ("AboutPage", None),
        "apoie": ("WebPage", None),
    }
    for name, (kind, listing) in hubs.items():
        url = BASE + "/" + name + ".html"
        file = pub / (name + ".html")
        if _published(file, url):
            graph = [{"@type": kind, "@id": url + "#page", "url": url,
                      "inLanguage": "pt-BR", "isPartOf": {"@id": BASE + "/#website"}}]
            if listing:
                graph[0]["mainEntity"] = listing
            _metadata(file, graph)

    # Translated editions (news_i18n.py, build-column.py): each page reuses the lastmod of its Portuguese original.
    mods = {u: m for u, m in entries if m}
    for lang in ("en", "es"):
        pages = []
        for kind in ("noticias", "coluna"):
            for f in sorted((pub / lang / kind).glob("*/index.html")):
                pages.append((BASE + "/" + lang + "/" + kind + "/" + f.parent.name + "/", mods.get(BASE + "/" + kind + "/" + f.parent.name + "/")))
        if (pub / lang / "index.html").is_file():
            entries.append((BASE + "/" + lang + "/", max((m for _, m in pages if m), default=None)))
        entries.extend(pages)
    # Hubs (home, noticias.html, coluna.html...) change whenever any article does: use the newest article date.
    newest = max((m for _, m in entries if m), default=None)
    entries = [(u, m or (newest if u == BASE + "/" or u.endswith(".html") else None)) for u, m in entries]
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, modified in entries:
        sitemap.append("  <url><loc>" + xml_escape(url) + "</loc>" +
                       ("<lastmod>" + xml_escape(modified) + "</lastmod>" if modified else "") +
                       "</url>")
    sitemap.append("</urlset>")
    _write_if_changed(pub / "sitemap.xml", "\n".join(sitemap) + "\n")
    column_count = _write_column_sitemap(pub, entries, essays)
    news_count = _write_news_sitemap(pub, recent_news, today)
    return {"sitemap_urls": len(entries), "news": len(linked_news), "essays": len(essays),
            "column_sitemap": column_count, "news_sitemap": news_count}


def _write_column_sitemap(pub: Path, entries, essays):
    columns = []
    for url, modified in entries:
        if url.startswith(BASE + "/coluna/"):
            columns.append((url, modified))
            continue
        match = re.fullmatch(re.escape(BASE) + r"/(en|es)/coluna/([^/]+)/", url)
        if not match:
            continue
        lang, slug = match.groups()
        item = essays.get(slug)
        translation = item.get(lang) if isinstance(item, dict) else None
        if not isinstance(translation, dict):
            continue
        title = translation.get("title")
        paragraphs = translation.get("paragraphs")
        if (not isinstance(title, str) or not title.strip() or
                not isinstance(paragraphs, list) or not paragraphs or
                not all(isinstance(paragraph, str) and paragraph.strip()
                        for paragraph in paragraphs)):
            continue
        page = pub / lang / "coluna" / slug / "index.html"
        if _published(page, url):
            columns.append((url, modified))
    latest = max((modified for _, modified in columns if modified), default=None)
    if any(url == BASE + "/coluna.html" for url, _ in entries):
        columns.insert(0, (BASE + "/coluna.html", latest))
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, modified in columns:
        rows.append("  <url><loc>" + xml_escape(url) + "</loc>" +
                    ("<lastmod>" + xml_escape(modified) + "</lastmod>" if modified else "") +
                    "</url>")
    rows.append("</urlset>")
    _write_if_changed(pub / "sitemap-coluna.xml", "\n".join(rows) + "\n")
    return len(columns)


def _write_news_sitemap(pub: Path, items, today=None):
    """Google News sitemap: only articles published in the last two days (max 1000), refreshed on every build."""
    today = today or datetime.now(timezone(timedelta(hours=-3))).date()  # Brasília, sem horário de verão
    oldest = (today - timedelta(days=2)).isoformat()
    recent = [x for x in items if x[2] >= oldest][:1000]
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">']
    for url, title, published in recent:
        rows.append("  <url><loc>" + xml_escape(url) + "</loc><news:news><news:publication>"
                    "<news:name>Raven Crow</news:name><news:language>pt</news:language></news:publication>"
                    "<news:publication_date>" + published + "</news:publication_date>"
                    "<news:title>" + xml_escape(title) + "</news:title></news:news></url>")
    rows.append("</urlset>")
    _write_if_changed(pub / "sitemap-news.xml", "\n".join(rows) + "\n")
    # robots.txt é reescrito pelo build-raven.py; garante a linha do sitemap de notícias depois dele
    robots = pub / "robots.txt"
    line = "Sitemap: " + BASE + "/sitemap-news.xml"
    text = robots.read_text(encoding="utf-8") if robots.exists() else "User-agent: *\nAllow: /\nSitemap: " + BASE + "/sitemap.xml\n"
    if line not in text:
        _write_if_changed(robots, text.rstrip("\n") + "\n" + line + "\n")
    return len(recent)


if __name__ == "__main__":
    print(json.dumps(build(Path(__file__).resolve().parent), ensure_ascii=False))
