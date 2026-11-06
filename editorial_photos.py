"""Conservative Wikimedia Commons photo discovery with license/source metadata and safe fallback."""
import json
import re
import html
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT="RavenCrowEditorial/1.0 (https://ravencrow.cloud; Wikimedia Commons attribution)"
LICENSES={'CC BY 4.0','CC BY-SA 4.0','CC BY 3.0','CC BY-SA 3.0','CC0','Public domain'}
STOP={'para','sobre','como','com','uma','das','dos','por','que','de','do','da','em','no','na','os','as','e','a','o','um','novo','nova','brasil','governo','politica','política','entenda','entender','2026'}
def keywords(title):
    return {w for w in re.findall(r'[a-zà-ú0-9]+',title.lower()) if len(w)>=4 and w not in STOP}
def choose_candidate(article,candidates):
    terms=keywords(article.get('title',''))
    if len(terms)<2:return None
    for c in candidates:
        name=c.get('title','').lower()
        matched=sum(1 for w in terms if re.search(r'(?<!\w)'+re.escape(w)+r'(?!\w)',name))
        if matched<2 or matched/max(1,len(terms))<.5:continue
        if c.get('license') not in LICENSES:continue
        if not c.get('url','').startswith('https://upload.wikimedia.org/'):continue
        if not c.get('page','').startswith('https://commons.wikimedia.org/'):continue
        if c.get('width',0)<650 or c.get('height',0)<350:continue
        return c
    return None
def clean(s):
    return html.unescape(re.sub(r'<[^>]*>','',str(s or ''))).strip()
def search_commons(article):
    terms=sorted(keywords(article.get('title','')),key=len,reverse=True)[:5]
    if len(terms)<2:return []
    query=' '.join(terms[:4])+' filetype:bitmap'
    params=urllib.parse.urlencode({'action':'query','generator':'search','gsrsearch':query,'gsrnamespace':6,'gsrlimit':8,'prop':'imageinfo','iiprop':'url|size|extmetadata','iiurlwidth':1200,'format':'json'})
    req=urllib.request.Request('https://commons.wikimedia.org/w/api.php?'+params,headers={'User-Agent':USER_AGENT})
    with urllib.request.urlopen(req,timeout=9) as resp: data=json.load(resp)
    found=[]
    for page in data.get('query',{}).get('pages',{}).values():
        info=(page.get('imageinfo') or [{}])[0]
        meta=info.get('extmetadata') or {}
        license_name=clean(meta.get('LicenseShortName',{}).get('value',''))
        if license_name=='CC BY-SA 4.0 International':license_name='CC BY-SA 4.0'
        found.append({'title':page.get('title',''),'license':license_name,'url':info.get('thumburl') or info.get('url',''),'page':info.get('descriptionurl',''),'width':info.get('width',0),'height':info.get('height',0),'artist':clean(meta.get('Artist',{}).get('value',''))[:200]})
    return found
def download_photo(url):
    req=urllib.request.Request(url,headers={'User-Agent':USER_AGENT})
    with urllib.request.urlopen(req,timeout=12) as resp:
        if not resp.headers.get('Content-Type','').lower().startswith('image/jpeg'):return b''
        data=resp.read(3_000_001)
        return data if len(data)<=3_000_000 and data.startswith(b'\xff\xd8\xff') else b''
def fetch_photos(public,articles):
    dest=public/'editorial'/'photos';dest.mkdir(parents=True,exist_ok=True)
    manifest_path=public/'editorial-photo-credits.json'
    try: existing=json.loads(manifest_path.read_text(encoding='utf-8'))
    except (FileNotFoundError,ValueError):existing={}
    result=dict(existing)
    for a in articles:
        slug=str(a.get('id',''))
        if not re.fullmatch(r'[a-z0-9-]{3,100}',slug):continue
        if slug in result and (public/result[slug]['path']).is_file():continue
        try:
            candidate=choose_candidate(a,search_commons(a))
            if not candidate:continue
            data=download_photo(candidate['url'])
            if len(data)<1024:continue
            path=dest/(slug+'.jpg')
            path.write_bytes(data)
            result[slug]={'path':'editorial/photos/'+slug+'.jpg','source':candidate['page'],'license':candidate['license'],'artist':candidate.get('artist',''),'commons_title':candidate['title']}
        except (OSError,ValueError,KeyError,TimeoutError):
            continue
    manifest_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
