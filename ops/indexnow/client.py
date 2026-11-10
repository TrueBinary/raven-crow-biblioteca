"""Bounded HTTP operations. Only submit_batch can make a POST."""
import json
import re
import secrets
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from .snapshot import HOST, parse_page

ENDPOINT='https://api.indexnow.org/indexnow'
USER_AGENT='RavenCrow-IndexNow/1.0'
@dataclass(frozen=True)
class Config:
    host: str
    key: str
    key_location: str
    repo: str
    released_sha_file: str
    state_db: str
    log_file: str
    endpoint: str=ENDPOINT
    enabled: bool=False

@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: dict[str,str]
    body: bytes

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

class UrllibTransport:
    def __init__(self):
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    def request(self,method,url,*,json_body=None,timeout=10):
        headers={'User-Agent':USER_AGENT}
        data=None
        if json_body is not None:
            headers['Content-Type']='application/json; charset=utf-8';data=json.dumps(json_body).encode()
        req=urllib.request.Request(url,data=data,headers=headers,method=method)
        try: response=self.opener.open(req,timeout=timeout)
        except urllib.error.HTTPError as e: response=e
        with response:
            body=response.read((8<<20)+1)
            if len(body)>8<<20:raise ValueError('response exceeds 8 MiB')
            return HttpResult(response.status,{k.lower():v for k,v in response.headers.items()},body)

def valid_url(url):
    p=urlsplit(url)
    return p.scheme=='https' and p.netloc=='ravencrow.cloud' and not (p.query or p.fragment) and p.path.startswith('/') and not any(c in url for c in ['\\','\r','\n','\x00']) and '..' not in p.path and '%' not in p.path

def load_config(path):
    c=Config(**json.loads(Path(path).read_text(encoding='utf-8-sig')))
    if c.host!=HOST or c.endpoint!=ENDPOINT or not re.fullmatch('[a-f0-9]{32}',c.key) or c.key_location!=HOST+'/'+c.key+'.txt' or not isinstance(c.enabled,bool):
        raise ValueError('invalid IndexNow configuration')
    return c

def create_key_artifact(output_dir):
    output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    if list(output_dir.glob('*.txt')): raise FileExistsError('existing key artifact; reuse it')
    key=secrets.token_hex(16);path=output_dir/(key+'.txt')
    with path.open('x',encoding='utf-8',newline='') as f:f.write(key)
    return key,path

def verify_key(config,transport):
    r=transport.request('GET',config.key_location,timeout=10)
    mime=r.headers.get('content-type','').split(';')[0].strip()
    if r.status!=200 or r.body!=config.key.encode() or mime not in ('text/plain',''):
        raise ValueError('public ownership key is not exact plain text')

def verify_page(item,transport):
    if not valid_url(item.url):return False
    robots=transport.request('GET',HOST+'/robots.txt',timeout=10)
    if robots.status!=200:return False
    parser=urllib.robotparser.RobotFileParser();parser.parse(robots.body.decode('utf-8').splitlines())
    if not parser.can_fetch(USER_AGENT,item.url) or not parser.can_fetch('*',item.url):return False
    r=transport.request('GET',item.url,timeout=10)
    if item.kind=='remove':return r.status in (404,410)
    if r.status!=200 or re.search(r'\b(noindex|none)\b',r.headers.get('x-robots-tag','').lower()):return False
    try:return parse_page(r.body.decode('utf-8'),item.url).fingerprint==item.fingerprint
    except (ValueError,UnicodeError):return False

def submit_batch(config,urls,transport):
    urls=list(dict.fromkeys(urls))
    if not urls or len(urls)>100 or not all(valid_url(u) for u in urls): raise ValueError('invalid IndexNow URL batch')
    return transport.request('POST',config.endpoint,json_body={'host':'ravencrow.cloud','key':config.key,'keyLocation':config.key_location,'urlList':urls},timeout=10)
