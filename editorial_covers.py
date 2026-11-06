"""Generate a branded, deterministic visual for each published article without an approved photo."""
from pathlib import Path
import html
import re
import textwrap

def build_covers(public: Path, articles: list[dict]) -> dict[str,str]:
    out=public/'editorial'/'covers'
    out.mkdir(parents=True,exist_ok=True)
    mapping={}
    for article in articles:
        slug=str(article.get('id',''))
        if not re.fullmatch(r'[a-z0-9-]{3,100}',slug):
            continue
        title=' '.join(str(article.get('title','Raven Crow')).split())
        category=' '.join(str(article.get('category','NOTÍCIAS')).split())[:38]
        words=title.split()
        lines=[]
        current=''
        for word in words:
            candidate=(current+' '+word).strip()
            if len(candidate)>25 and current:
                lines.append(current)
                current=word
            else: current=candidate
        if current: lines.append(current)
        if len(lines)>5:
            lines=lines[:4]+[' '.join(lines[4:])[:26]+'…']
        font_size=59 if len(lines)<=4 else 49
        text=''.join(f'<text x="92" y="{250+i*(font_size+15)}" font-size="{font_size}" font-weight="900" font-family="Arial,sans-serif" fill="#ffffff">{html.escape(line)}</text>' for i,line in enumerate(lines))
        svg=f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675" role="img" aria-label="Capa editorial: {html.escape(title,quote=True)}">
<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#09090c"/><stop offset=".6" stop-color="#211015"/><stop offset="1" stop-color="#6b1722"/></linearGradient></defs>
<rect width="1200" height="675" fill="url(#bg)"/>
<path d="M820 0 L1200 0 L1200 675 L1030 675 Z" fill="#b51d2d" opacity=".17"/>
<path d="M1060 0 L1200 0 L1200 675 L1140 675 Z" fill="#ee3e49" opacity=".16"/>
<rect x="92" y="85" width="80" height="7" fill="#ed3d48"/>
<text x="92" y="138" font-size="28" letter-spacing="4" font-family="Arial,sans-serif" font-weight="bold" fill="#f16d73">{html.escape(category)}</text>
{text}
<rect x="92" y="605" width="1016" height="1" fill="#ffffff" opacity=".27"/>
<text x="92" y="642" font-size="25" font-weight="bold" letter-spacing="5" font-family="Arial,sans-serif" fill="#ffffff">RAVEN CROW  /  JORNALISMO &amp; ANÁLISE</text>
</svg>"""
        target=out/(slug+'.svg')
        if not target.exists() or target.read_text(encoding='utf-8')!=svg:
            target.write_text(svg,encoding='utf-8')
        mapping[slug]='editorial/covers/'+slug+'.svg'
    return mapping
