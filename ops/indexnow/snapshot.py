"""Canonical page snapshots from immutable Git commits, never the working tree."""
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from pathlib import Path

HOST = 'https://ravencrow.cloud'

@dataclass(frozen=True)
class PageRevision:
    url: str
    source_path: str
    fingerprint: str

def key_to_url(path: str) -> str | None:
    if path == 'index.html': return HOST + '/'
    if not path.startswith('public/') or '..' in path: return None
    key = path[7:]
    if key in ('noticias.html','coluna.html','livros.html','sobre.html','apoie.html','termos.html','privacidade.html'):
        return HOST + '/' + key.removesuffix('.html')
    if re.fullmatch(r'en/(?:news|column|library|support|about|terms|privacy)\.html|es/(?:noticias|columna|libros|apoyo|sobre|terminos|privacidad)\.html',key):
        return HOST + '/' + key.removesuffix('.html')
    if key in ('en/index.html','es/index.html'):
        return HOST + '/' + key.removesuffix('index.html')
    if re.fullmatch(r'(?:en/(?:news|column)|es/(?:noticias|columna)|noticias|coluna)/[a-z0-9-]{3,100}/index\.html',key):
        return HOST + '/' + key.removesuffix('index.html')
    return None

class EditorialParser(HTMLParser):
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[]; self.title=[]; self.text=[]; self.images=[]
        self.canonical=''; self.description=''; self.noindex=False; self.has_main=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs); blocked=(self.stack[-1][1] if self.stack else False)
        blocked |= tag in ('script','style','aside') or 'hidden' in a or a.get('aria-hidden','').lower()=='true'
        in_main = tag=='main' or (self.stack[-1][2] if self.stack else False)
        if tag=='main': self.has_main=True
        if tag=='link' and 'canonical' in a.get('rel','').lower().split(): self.canonical=a.get('href','')
        if tag=='meta':
            if a.get('name','').lower()=='description': self.description=a.get('content','')
            if a.get('name','').lower() in ('robots','googlebot'):
                self.noindex |= bool(re.search(r'\b(noindex|none)\b',a.get('content','').lower()))
        if in_main and not blocked and tag=='img': self.images.append([a.get(k,'') for k in ('src','srcset','alt')])
        if tag not in self.VOID: self.stack.append((tag,blocked,in_main))
        elif tag in ('br','hr') and in_main and not blocked: self.text.append(' ')
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in self.VOID: self.handle_endtag(tag)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                if self.stack[i][2] and not self.stack[i][1] and tag in ('p','div','h1','h2','h3','li','section'): self.text.append(' ')
                del self.stack[i:]; break
    def handle_data(self,data):
        if self.stack and not self.stack[-1][1]:
            if any(x[0]=='title' for x in self.stack): self.title.append(data)
            if self.stack[-1][2]: self.text.append(data)

def parse_page(html: str, expected_url: str) -> PageRevision:
    p=EditorialParser(); p.feed(html)
    if not p.has_main or p.canonical != expected_url or p.noindex:
        raise ValueError('ineligible HTML (main/canonical/noindex): '+expected_url)
    norm=lambda s:' '.join(s.split())
    content=[norm(''.join(p.title)),norm(p.description),p.canonical,norm(''.join(p.text)),p.images]
    digest=hashlib.sha256(json.dumps(content,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    return PageRevision(expected_url,'',digest)

def read_snapshot(repo: Path, sha: str) -> dict[str,PageRevision]:
    if not re.fullmatch('[a-f0-9]{40}',sha): raise ValueError('invalid published commit')
    def git(*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True,encoding='utf-8',errors='strict',timeout=15)
    git('cat-file','-e',sha+'^{commit}')
    result={}
    for path in git('ls-tree','-r','--name-only',sha,'--','index.html','public').splitlines():
        url=key_to_url(path)
        if url:
            result[url]=replace(parse_page(git('show',sha+':'+path),url),source_path=path)
    if not result: raise ValueError('empty published snapshot')
    return result
