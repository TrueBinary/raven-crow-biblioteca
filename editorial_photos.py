"""Discover accurately labeled Wikimedia Commons archive photos for Raven Crow news."""
from pathlib import Path
import html
import json
import re
import urllib.parse
import urllib.request

USER_AGENT="RavenCrowEditorial/1.0 (https://ravencrow.cloud; Wikimedia Commons attribution)"
LICENSES={
    "CC BY 2.0", "CC BY 3.0", "CC BY 4.0",
    "CC BY-SA 2.0", "CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0",
    "CC0", "Public domain",
}
STOP={"para","sobre","como","com","uma","das","dos","por","que","de","do","da",
      "em","no","na","os","as","e","a","o","um","novo","nova","brasil",
      "governo","politica","política","entenda","entender","2026"}

# Contextual archive imagery, NOT a claim that the photo depicts the current event.
# Files were chosen from Wikimedia Commons search results, with licenses rechecked by API at build.
CURATED_FILES={
    "cmo-creditos-roraima-regra-de-ouro-2026":"File:Brasilia National Congress Buildings.jpg",
    "sac-atendimento-humano-2026":"File:Callcentre.jpg",
    "record-kids-classificacao-12-anos-2026":"File:Holy bible book.jpg",
    "mercosul-efta-noruega-2026":"File:Nossa Brasília - Bandeira Nacional (27878027722).jpg",
    "eleicoes-2026":"File:Brazilian DRE voting machine for 2022 elections.jpg",
    "contas-publicas-2026":'File:Edifício "Sede" do Banco Central do Brasil em Brasília.jpg',
    "inflacao-poder-compra":"File:20 Brazilian Real banknote featuring a Golden Lion Tamarin monkey.jpg",
}
ALLOWED_HOSTS={"upload.wikimedia.org","thumb.wikimedia.org"}

def clean(s):
    return html.unescape(re.sub(r"<[^>]*>","",str(s or ""))).strip()

def keywords(title):
    return {w for w in re.findall(r"[a-zà-ú0-9]+",title.lower()) if len(w)>=4 and w not in STOP}

def is_usable(c):
    uri=urllib.parse.urlparse(c.get("url",""))
    page=urllib.parse.urlparse(c.get("page",""))
    return (uri.scheme=="https" and uri.hostname in ALLOWED_HOSTS
            and page.scheme=="https" and page.hostname=="commons.wikimedia.org"
            and c.get("license") in LICENSES
            and c.get("width",0)>=650 and c.get("height",0)>=350
            and str(c.get("title","")).startswith("File:"))

def choose_candidate(article,candidates):
    terms=keywords(article.get("title",""))
    if len(terms)<2:return None
    for c in candidates:
        if not is_usable(c):continue
        name=c.get("title","").lower()
        matched=sum(bool(re.search(r"(?<!\w)"+re.escape(w)+r"(?!\w)",name)) for w in terms)
        if matched>=2 and matched/max(1,len(terms))>=.5:return c
    return None

def _commons_api(params):
    query=urllib.parse.urlencode({"format":"json",**params})
    req=urllib.request.Request("https://commons.wikimedia.org/w/api.php?"+query,
                               headers={"User-Agent":USER_AGENT})
    with urllib.request.urlopen(req,timeout=10) as response:
        return json.load(response)

def _candidate_from_page(page):
    info=(page.get("imageinfo") or [{}])[0]
    meta=info.get("extmetadata") or {}
    lic=clean(meta.get("LicenseShortName",{}).get("value",""))
    if lic=="CC BY-SA 4.0 International":lic="CC BY-SA 4.0"
    return {"title":page.get("title",""),"license":lic,
            "url":info.get("thumburl") or info.get("url",""),
            "page":info.get("descriptionurl",""),
            "width":info.get("width",0),"height":info.get("height",0),
            "artist":clean(meta.get("Artist",{}).get("value",""))[:250]}

def lookup_commons(title):
    data=_commons_api({"action":"query","titles":title,"prop":"imageinfo",
                       "iiprop":"url|size|extmetadata","iiurlwidth":"1200"})
    for page in data.get("query",{}).get("pages",{}).values():
        c=_candidate_from_page(page)
        if c["title"].replace("_"," ")==title.replace("_"," "):
            return c
    return None

def search_commons(article):
    terms=sorted(keywords(article.get("title","")),key=len,reverse=True)[:5]
    if len(terms)<2:return []
    data=_commons_api({"action":"query","generator":"search",
                      "gsrsearch":" ".join(terms[:4])+" filetype:bitmap",
                      "gsrnamespace":"6","gsrlimit":"8","prop":"imageinfo",
                      "iiprop":"url|size|extmetadata","iiurlwidth":"1200"})
    return [_candidate_from_page(page) for page in data.get("query",{}).get("pages",{}).values()]

def download_photo(url):
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!="https" or parsed.hostname not in ALLOWED_HOSTS:return b""
    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT})
    with urllib.request.urlopen(req,timeout=12) as response:
        if response.headers.get_content_type()!="image/jpeg":return b""
        data=response.read(3_000_001)
        return data if len(data)<=3_000_000 and data.startswith(b"\xff\xd8\xff") else b""

def fetch_photos(public:Path,articles:list[dict]):
    dest=public/"editorial"/"photos"
    dest.mkdir(parents=True,exist_ok=True)
    manifest_path=public/"editorial-photo-credits.json"
    try:existing=json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError,ValueError):existing={}
    result=dict(existing) if isinstance(existing,dict) else {}
    for article in articles:
        slug=str(article.get("id",""))
        if not re.fullmatch(r"[a-z0-9-]{3,100}",slug):continue
        target=dest/(slug+".jpg")
        if (slug in result and target.is_file() and result[slug].get("path")==f"editorial/photos/{slug}.jpg"
            and (slug not in CURATED_FILES or result[slug].get("commons_title")==CURATED_FILES[slug])):
            continue
        try:
            curated=CURATED_FILES.get(slug)
            candidate=lookup_commons(curated) if curated else choose_candidate(article,search_commons(article))
            if not candidate or not is_usable(candidate):continue
            if curated and candidate.get("title","").replace("_"," ")!=curated.replace("_"," "):
                continue
            data=download_photo(candidate["url"])
            if len(data)<1024:continue
            target.write_bytes(data)
            result[slug]={"path":f"editorial/photos/{slug}.jpg",
                          "source":candidate["page"],"license":candidate["license"],
                          "artist":candidate.get("artist",""),
                          "commons_title":candidate["title"],
                          "illustrative":True}
        except (OSError,ValueError,KeyError,TimeoutError):
            continue
    manifest_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result

def render_credits_page(public:Path,credits:dict,articles:list[dict]):
    article_names={a.get("id"):a.get("title","Notícia") for a in articles}
    rows=[]
    for slug,credit in sorted(credits.items()):
        source=str(credit.get("source",""))
        if not source.startswith("https://commons.wikimedia.org/"):continue
        lic=credit.get("license","")
        if lic=="CC0":license_url="https://creativecommons.org/publicdomain/zero/1.0/"
        elif lic=="Public domain":license_url="https://creativecommons.org/publicdomain/mark/1.0/"
        elif lic.startswith("CC BY-SA "):license_url="https://creativecommons.org/licenses/by-sa/"+lic.split()[-1]+"/"
        elif lic.startswith("CC BY "):license_url="https://creativecommons.org/licenses/by/"+lic.split()[-1]+"/"
        else:continue
        e=lambda s:html.escape(str(s),quote=True)
        artist=credit.get("artist") or "Autoria indicada na página de origem"
        rows.append('<li><h2>'+e(article_names.get(slug,slug))+'</h2><p>Imagem ilustrativa de arquivo: '+e(credit.get("commons_title",""))+'</p>'
                    '<p>Autoria: '+e(artist)+' · <a href="'+e(source)+'" rel="noopener noreferrer">Arquivo original e créditos</a>'
                    ' · <a href="'+e(license_url)+'" rel="noopener noreferrer">'+e(lic)+'</a></p></li>')
    body="".join(rows) if rows else "<p>Não há fotografias externas publicadas nesta edição.</p>"
    content='''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Créditos das fotografias | Raven Crow</title>
<style>body{margin:0;background:#0b0c0f;color:#f6f3f3;font:16px/1.6 system-ui,Arial,sans-serif}
main{max-width:850px;margin:auto;padding:44px 22px 80px}h1{font-size:clamp(32px,6vw,56px);line-height:1.1}
h1,h2{font-weight:900}h2{font-size:22px;margin:0 0 8px}li{padding:24px 0;border-top:1px solid #34343a}
ul{list-style:none;padding:0}p{color:#c5c0c0}a{color:#ff777d}small{color:#e0b2b2}</style></head>
<body><main><a href="index.html">← Raven Crow</a><h1>Créditos das fotografias</h1>
<p>As fotos são imagens ilustrativas de arquivo e não devem ser interpretadas como registros dos acontecimentos narrados.</p>
<ul>'''+body+'''</ul></main></body></html>'''
    target=public/"creditos-fotos.html"
    target.write_text(content,encoding="utf-8")
    return target
