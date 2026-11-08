"""Documentary photos on news article pages: main photo on top, up to two extras inside the text.

Credits live in public/editorial-photo-credits.json: "<id>" is the main photo, "<id>--2" and "<id>--3" are extras
with "placement" = "fatos" | "analise" | "contraponto" (anything else goes after the analysis).
"""
from pathlib import Path

from column_photos import photo_figure

PLACEMENTS = ("fatos", "analise", "contraponto")
STYLE = ('<style>.rc-col-story-photo{margin:22px 0;border:1px solid rgba(255,255,255,.12);border-radius:10px;overflow:hidden;'
         'background:#111216}.rc-col-story-photo img{display:block;width:100%;height:auto;max-height:520px;object-fit:cover}'
         '.rc-col-story-photo figcaption{padding:10px 14px;font-size:.82rem;line-height:1.4;color:rgba(255,255,255,.72);'
         'border-top:2px solid #E42E3B}</style>')


def news_figures(slug: str, credits: dict, public: Path, title: str, prefix: str = "") -> dict:
    out = {"top": "", "fatos": "", "analise": "", "contraponto": "", "style": ""}
    out["top"] = photo_figure(slug, credits, public, title, prefix)
    for n in (2, 3):
        key = f"{slug}--{n}"
        fig = photo_figure(key, credits, public, title, prefix)
        if fig:
            where = (credits.get(key) or {}).get("placement")
            out[where if where in PLACEMENTS else "analise"] += fig
    if any(out[k] for k in ("top",) + PLACEMENTS):
        out["style"] = STYLE
    return out
