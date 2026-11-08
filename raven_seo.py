"""Add structured data and maintain a canonical sitemap for published Raven Crow pages.

Static, offline and idempotent. Never changes editorial text, styles, ads or media.
Safe to call after any of the existing site builders.
"""
from __future__ import annotations

from datetime import date
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


def build(root: Path) -> dict:
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
        _metadata(file, [article, _crumbs("Coluna", item.get("title", ""), url)],
                  published=published, modified=article["dateModified"])
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

    # Translated editions (news_i18n.py): /<lang>/ and every /<lang>/noticias/<id>/ page that exists.
    for lang in ("en", "es"):
        if (pub / lang / "index.html").is_file():
            entries.append((BASE + "/" + lang + "/", None))
        for f in sorted((pub / lang / "noticias").glob("*/index.html")):
            entries.append((BASE + "/" + lang + "/noticias/" + f.parent.name + "/", None))
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, modified in entries:
        sitemap.append("  <url><loc>" + xml_escape(url) + "</loc>" +
                       ("<lastmod>" + xml_escape(modified) + "</lastmod>" if modified else "") +
                       "</url>")
    sitemap.append("</urlset>")
    _write_if_changed(pub / "sitemap.xml", "\n".join(sitemap) + "\n")
    return {"sitemap_urls": len(entries), "news": len(linked_news), "essays": len(essays)}


if __name__ == "__main__":
    print(json.dumps(build(Path(__file__).resolve().parent), ensure_ascii=False))
