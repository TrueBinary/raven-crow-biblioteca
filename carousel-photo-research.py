"""Find reusable documentary photos on Wikimedia Commons, record attribution and license.
Requires explicit editorial review before publishing; never guesses image identity.
"""
import argparse,json,urllib.parse,urllib.request,html,re
from pathlib import Path
API="https://commons.wikimedia.org/w/api.php"
UA="RavenCrowEditorial/1.0 (image research; contact via project repository)"
def get(params):
    url=API+"?"+urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":UA}),timeout=25) as response:
        return json.load(response)
def clean(text):
    return re.sub(r"<[^>]+>"," ",html.unescape(text or "")).strip()
def candidates(query,limit=12):
    data=get({"action":"query","generator":"search","gsrsearch":query+" filetype:bitmap","gsrnamespace":6,"gsrlimit":limit,"prop":"imageinfo","iiprop":"url|extmetadata|size","iiurlwidth":1600,"format":"json"})
    found=[]
    for page in data.get("query",{}).get("pages",{}).values():
        for info in page.get("imageinfo",[]):
            meta=info.get("extmetadata",{})
            license_code=clean(meta.get("LicenseShortName",{}).get("value",""))
            if not (license_code.startswith("CC BY") or license_code in ("CC0","Public domain")):continue
            if info.get("width",0)<1080 or info.get("height",0)<900:continue
            link=info.get("thumburl") or info.get("url")
            if not link:continue
            found.append({"title":page["title"],"url":link,"page":info.get("descriptionurl"),"license":license_code,"artist":clean(meta.get("Artist",{}).get("value","")),"credit":clean(meta.get("Credit",{}).get("value","")),"width":info["width"],"height":info["height"]})
    return sorted(found,key=lambda x:x["width"]*x["height"],reverse=True)
def main():
    p=argparse.ArgumentParser();p.add_argument("query");p.add_argument("output");a=p.parse_args()
    results=candidates(a.query)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"query":a.query,"status":"REQUIRES_EDITORIAL_SELECTION","candidates":results},ensure_ascii=False,indent=2),encoding="utf-8")
    print("candidates",len(results),"file",out)
if __name__=="__main__":main()
