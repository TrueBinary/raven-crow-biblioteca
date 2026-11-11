"""Optional documentary photo for a Coluna do Corvo essay, taken from public/editorial-photo-credits.json."""
from html import escape
from pathlib import Path
import re

WIDTHS = (320, 640, 1280)


def webp_variants(public: Path, path: str) -> dict:
    """Smaller WebP copies of a credited JPEG next to it (`<name>-640.webp`, `<name>-1280.webp`), made once.

    Returns {"src", "srcset", "width", "height"} for the <img>, or {} when the JPEG cannot be read.
    """
    src = public / path
    try:
        from PIL import Image
        with Image.open(src) as im:
            w, h = im.size
            widths = sorted({x for x in WIDTHS if x < w} | {min(w, WIDTHS[-1])})
            for width in widths:
                out = src.with_name(f"{src.stem}-{width}.webp")
                if not out.is_file() or out.stat().st_mtime < src.stat().st_mtime:
                    im.convert("RGB").resize((width, round(h * width / w)), Image.LANCZOS).save(out, "WEBP", quality=78)
    except Exception:  # missing Pillow, broken or placeholder file: keep the original JPEG
        return {}
    rel = lambda width: f"{path[:-4]}-{width}.webp"
    return {"src": rel(widths[-1]), "srcset": ", ".join(f"{rel(x)} {x}w" for x in widths),
            "width": widths[-1], "height": round(h * widths[-1] / w)}


def photo_figure(slug: str, credits: dict, public: Path, title: str, prefix: str = "") -> str:
    """Return the <figure> for the essay's credited photo, or "" when there is none or it is incomplete."""
    c = credits.get(slug) or {}
    path = c.get("path", "")
    if not re.fullmatch(r"editorial/photos/[a-z0-9-]+\.jpg", path) or not (public / path).is_file() or not c.get("artist"):
        return ""
    caption = c.get("caption") or ""
    credit = "Foto: " + c["artist"]
    text = f"{caption} · {credit}" if caption else credit
    v = webp_variants(public, path)
    img = (f'src="{escape(prefix + v["src"], quote=True)}" srcset="{escape(", ".join(prefix + s for s in v["srcset"].split(", ")), quote=True)}" '
           f'sizes="(max-width: 900px) 100vw, 900px" width="{v["width"]}" height="{v["height"]}"' if v else f'src="{escape(prefix + path, quote=True)}"')
    return (f'<figure class="rc-col-story-photo"><img {img} alt="{escape(caption or title, quote=True)}" '
            f'loading="eager" decoding="async"><figcaption>{escape(text)}</figcaption></figure>')
