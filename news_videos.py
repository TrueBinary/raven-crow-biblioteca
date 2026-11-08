"""Videos inside news articles, from the article's "videos" list.

Each item: {"youtube": "<url or 11-char id>", "start": <seconds, optional>, "credit": "<channel>"}
        or {"clip": "clips/<sha256>.mp4"}   (a Raven Crow cut already published to the site)
plus "placement": "top" | "fatos" | "analise" | "contraponto" (default "fatos") and "caption".
YouTube is shown as a thumbnail that loads the youtube-nocookie player only on click (fast page, no tracking
until play); without JavaScript the thumbnail is a plain link to YouTube.
"""
import html
import re
from urllib.parse import urlparse, parse_qs

PLACEMENTS = ("top", "fatos", "analise", "contraponto")
STYLE = ('<style>.rc-video{margin:22px 0;border:1px solid rgba(255,255,255,.12);border-radius:10px;overflow:hidden;background:#111216}'
         '.rc-video video,.rc-yt,.rc-video iframe{display:block;width:100%;aspect-ratio:16/9;border:0;background:#000}'
         '.rc-video video.rc-vertical{aspect-ratio:9/16;max-height:640px;margin:0 auto}'
         '.rc-yt{position:relative}.rc-yt img{width:100%;height:100%;object-fit:cover;display:block}'
         '.rc-yt span{position:absolute;inset:0;margin:auto;width:72px;height:50px;border-radius:12px;background:#E42E3B;color:#fff;'
         'font:700 26px/50px sans-serif;text-align:center}'
         '.rc-video figcaption{padding:10px 14px;font-size:.82rem;line-height:1.4;color:rgba(255,255,255,.72);border-top:2px solid #E42E3B}</style>'
         '<script>document.addEventListener("click",function(e){var a=e.target.closest&&e.target.closest("a.rc-yt");if(!a)return;e.preventDefault();'
         'var f=document.createElement("iframe");f.src="https://www.youtube-nocookie.com/embed/"+a.dataset.yt+"?autoplay=1&start="+(a.dataset.start||0);'
         'f.allow="autoplay; encrypted-media; picture-in-picture";f.allowFullscreen=true;f.title=a.getAttribute("aria-label")||"Vídeo";a.replaceWith(f)});</script>')


def youtube_id(value) -> str:
    v = str(value or "").strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", v):
        return v
    u = urlparse(v)
    if u.scheme != "https" or not re.search(r"(^|\.)(youtube\.com|youtu\.be|youtube-nocookie\.com)$", u.hostname or ""):
        return ""
    cand = parse_qs(u.query).get("v", [""])[0] if u.path == "/watch" else u.path.rstrip("/").split("/")[-1]
    return cand if re.fullmatch(r"[A-Za-z0-9_-]{11}", cand) else ""


def news_videos(a: dict, prefix: str = "", captions: dict | None = None, play_label: str = "Assistir ao vídeo") -> dict:
    out = {k: "" for k in PLACEMENTS}
    out["style"] = ""
    esc = lambda v: html.escape(str(v or ""), quote=True)
    vids = a.get("videos") if isinstance(a.get("videos"), list) else []
    for n, v in enumerate(vids[:3], 1):
        if not isinstance(v, dict):
            continue
        cap = str((captions or {}).get(str(n)) or v.get("caption") or "")
        where = v.get("placement") if v.get("placement") in PLACEMENTS else "fatos"
        yid = youtube_id(v.get("youtube"))
        if yid:
            start = int(v["start"]) if str(v.get("start", "")).isdigit() else 0
            credit = ("Vídeo: " + str(v["credit"])) if v.get("credit") else ""
            text = " · ".join(x for x in (cap, credit) if x)
            out[where] += (f'<figure class="rc-video"><a class="rc-yt" href="https://www.youtube.com/watch?v={yid}&amp;t={start}s" '
                           f'data-yt="{yid}" data-start="{start}" aria-label="{esc(play_label + (": " + cap if cap else ""))}" rel="noopener" target="_blank">'
                           f'<img src="https://i.ytimg.com/vi/{yid}/hqdefault.jpg" alt="" loading="lazy" decoding="async"><span aria-hidden="true">▶</span></a>'
                           + (f"<figcaption>{esc(text)}</figcaption>" if text else "") + "</figure>")
            continue
        clip = str(v.get("clip") or "")
        if re.fullmatch(r"clips/[a-f0-9]{64}\.mp4", clip):
            poster = prefix + clip[:-4] + ".jpg"
            out[where] += (f'<figure class="rc-video"><video class="rc-vertical" controls preload="none" playsinline poster="{esc(poster)}" '
                           f'src="{esc(prefix + clip)}"{" aria-label=" + chr(34) + esc(cap) + chr(34) if cap else ""}></video>'
                           + (f"<figcaption>{esc(cap)} · Raven Crow</figcaption>" if cap else "") + "</figure>")
    if any(out[k] for k in PLACEMENTS):
        out["style"] = STYLE
    return out
