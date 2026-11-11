"""Último passo do build, em todas as páginas: fontes servidas pelo próprio site e versão no nome dos CSS/JS.

- Google Fonts custava duas idas à rede (fonts.googleapis + fonts.gstatic) antes do primeiro desenho (PageSpeed: ~1,2 s
  na página de matéria). As woff2 latin ficam em public/fonts/ e o @font-face vai inline, com preload do título.
- raven-*.css/js ganham ?v=<md5 do arquivo>: quem tem a página nova nunca usa o script velho do cache, e o Worker pode
  guardar esses arquivos por um ano.
"""
import hashlib
import re
from pathlib import Path

FONTS = [("Barlow Condensed", w, f"barlow-condensed-{w}") for w in (600, 700, 800, 900)] + [("DM Sans", "100 1000", "dm-sans")]
FONT_FACE = "".join(f"@font-face{{font-family:'{f}';font-style:normal;font-weight:{w};font-display:swap;src:url(/fonts/{n}.woff2) format('woff2')}}"
                    for f, w, n in FONTS)
FONT_HEAD = ('<link rel="preload" as="font" type="font/woff2" href="/fonts/barlow-condensed-900.woff2" crossorigin>'
             '<link rel="preload" as="font" type="font/woff2" href="/fonts/dm-sans.woff2" crossorigin>'
             f'<style data-fonts>{FONT_FACE}</style>')
GOOGLE = re.compile(r'<link rel="preconnect" href="https://fonts\.g[^>]*>\s*|<link (?:rel="stylesheet" )?href="https://fonts\.googleapis\.com/[^>]*>\s*')
ASSET = re.compile(r'((?:src|href)=")((?:\.\./)*/?(raven-[a-z0-9-]+\.(?:css|js)))(?:\?v=[^"]*)?"')


def finish_pages(public: Path, pages) -> int:
    """Reescreve as páginas que mudam; devolve quantas. Idempotente."""
    versions = {}

    def version(name):
        if name not in versions:
            f = public / name
            # LF como no git/R2: no Windows a cópia de trabalho é CRLF e o hash não bateria com a ETag do R2
            versions[name] = hashlib.md5(f.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:8] if f.is_file() else None
        return versions[name]

    def stamp(m):
        v = version(m.group(3))
        return f'{m.group(1)}{m.group(2)}?v={v}"' if v else m.group(0)

    changed = 0
    for page in pages:
        src = page.read_text(encoding="utf-8")
        out = src
        if GOOGLE.search(out):
            first = []
            out = GOOGLE.sub(lambda m: "" if first else first.append(1) or FONT_HEAD, out)
        out = ASSET.sub(stamp, out)
        if out != src:
            page.write_text(out, encoding="utf-8")
            changed += 1
    return changed


def site_pages(root: Path):
    return [root / "index.html"] + sorted((root / "public").rglob("*.html"))
