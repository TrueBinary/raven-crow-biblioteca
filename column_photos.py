"""Optional documentary photo for a Coluna do Corvo essay, taken from public/editorial-photo-credits.json."""
from html import escape
from pathlib import Path
import re


def photo_figure(slug: str, credits: dict, public: Path, title: str) -> str:
    """Return the <figure> for the essay's credited photo, or "" when there is none or it is incomplete."""
    c = credits.get(slug) or {}
    path = c.get("path", "")
    if not re.fullmatch(r"editorial/photos/[a-z0-9-]+\.jpg", path) or not (public / path).is_file() or not c.get("artist"):
        return ""
    caption = c.get("caption") or ""
    credit = "Foto: " + c["artist"]
    text = f"{caption} · {credit}" if caption else credit
    return (f'<figure class="rc-col-story-photo"><img src="{escape(path, quote=True)}" alt="{escape(caption or title, quote=True)}" '
            f'loading="eager" decoding="async"><figcaption>{escape(text)}</figcaption></figure>')
