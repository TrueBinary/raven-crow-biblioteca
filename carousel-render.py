"""Raven Crow carousel renderer. Requires Pillow. No publishing side effects."""
import argparse, hashlib, json, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W,H=1080,1350
PALETTE={"background":"#0D0E12","surface":"#18191F","text":"#F7F4ED","accent":"#E55E49","muted":"#A7A7AE"}
FONT=Path("C:/Windows/Fonts")
def face(size,bold=False):
    for name in (["arialbd.ttf","impact.ttf"] if bold else ["arial.ttf","segoeui.ttf"]):
        if (FONT/name).exists(): return ImageFont.truetype(str(FONT/name),size)
    return ImageFont.load_default()
def lines(draw,text,f,width):
    out=[]
    for paragraph in text.split("\n"):
        current=""
        for word in paragraph.split():
            candidate=(current+" "+word).strip()
            if current and draw.textbbox((0,0),candidate,font=f)[2]>width:
                out.append(current);current=word
            else: current=candidate
        out.append(current)
    return out
def render_slide(slide,index,total,brand_logo=None):
    im=Image.new("RGB",(W,H),PALETTE["background"]);d=ImageDraw.Draw(im)
    d.rectangle((0,0,16,H),fill=PALETTE["accent"])
    d.rectangle((64,78,1016,82),fill=PALETTE["accent"])
    d.text((64,100),"RAVEN CROW  /  O CORVO INVESTIGADOR",font=face(30,True),fill=PALETTE["text"])
    if brand_logo:
        logo=Image.open(brand_logo).convert("RGBA");logo.thumbnail((110,110))
        im.paste(logo,(900,145),logo)
    d.text((64,205),slide["section"].upper(),font=face(29,True),fill=PALETTE["accent"])
    y=275
    title=slide["title"].upper()
    for size in (82,72,62,54,46):
        f=face(size,True);wrapped=lines(d,title,f,940)
        if len(wrapped)*int(size*1.11)<390:break
    for line in wrapped:
        d.text((64,y),line,font=f,fill=PALETTE["text"]);y+=int(size*1.11)
    y+=40
    d.rectangle((64,y,290,y+8),fill=PALETTE["accent"]);y+=40
    if slide.get("image"):
        source=Image.open(slide["image"]).convert("RGB")
        source.thumbnail((950,360))
        im.paste(source,(64,y));y+=source.height+35
    body=slide["body"]
    for size in (43,39,35,31,27):
        f=face(size);wrapped=lines(d,body,f,935)
        if y+len(wrapped)*int(size*1.3)<1195:break
    if y+len(wrapped)*int(size*1.3)>=1195:raise ValueError("Text overflow on slide "+str(index))
    for line in wrapped:
        d.text((64,y),line,font=f,fill=PALETTE["text"]);y+=int(size*1.3)
    d.rectangle((64,1222,1016,1225),fill=PALETTE["surface"])
    d.text((64,1252),"RAVEN CROW  •  COLUNA DO CORVO",font=face(23,True),fill=PALETTE["accent"])
    d.text((944,1252),f"{index:02}/{total:02}",font=face(24,True),fill=PALETTE["text"])
    return im
def render_photo_slide(slide,index,total,brand_logo=None):
    """Photo-led editorial treatment; photo required, never silently replace with stock."""
    if not slide.get("image"): raise ValueError("Editorial photo style requires an image on each slide")
    source=Image.open(slide["image"]).convert("RGB")
    if min(source.size)<640: raise ValueError("Image resolution insufficient")
    im=Image.new("RGB",(W,H),PALETTE["background"])
    ratio=max(W/source.width,H/source.height)
    source=source.resize((int(source.width*ratio)+1,int(source.height*ratio)+1),Image.Resampling.LANCZOS)
    left=(source.width-W)//2;top=(source.height-H)//2
    im.paste(source.crop((left,top,left+W,top+H)))
    # Controlled dark overlay ensures contrast over unpredictable documentary photography.
    from PIL import ImageFilter
    overlay=Image.new("RGBA",(W,H),(0,0,0,0));o=ImageDraw.Draw(overlay)
    for y in range(H):
        darkness=32 if y<500 else min(237,32+int((y-500)*205/750))
        o.line((0,y,W,y),fill=(13,14,18,darkness))
    im=Image.alpha_composite(im.convert("RGBA"),overlay)
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,20),fill=PALETTE["accent"])
    d.rectangle((60,76,370,132),fill=PALETTE["background"])
    d.text((78,84),"RAVEN CROW",font=face(30,True),fill=PALETTE["text"])
    if brand_logo:
        logo=Image.open(brand_logo).convert("RGBA");logo.thumbnail((115,115))
        im.alpha_composite(logo,(900,85))
    y=708
    d.text((64,y),slide["section"].upper(),font=face(30,True),fill=PALETTE["accent"]);y+=54
    title=slide["title"].upper()
    body=slide.get("body","")
    body_font=face(31)
    body_lines=lines(d,body,body_font,925) if body else []
    if len(body_lines)>4: raise ValueError("Photo supporting text exceeds four lines")
    for size in (82,74,66,58,50,44):
        f=face(size,True);wrapped=lines(d,title,f,935)
        projected=y+len(wrapped)*int(size*1.07)+24+len(body_lines)*42
        if projected<1200:break
    if projected>=1200:raise ValueError("Photo headline/support overflow")
    for line in wrapped:
        d.text((64,y),line,font=f,fill=PALETTE["text"],stroke_width=2,stroke_fill=PALETTE["background"])
        y+=int(size*1.07)
    if body_lines:
        y+=20
        for line in body_lines:
            d.text((64,y),line,font=body_font,fill=PALETTE["text"],stroke_width=1,stroke_fill=PALETTE["background"])
            y+=42
    d.rectangle((64,1225,1018,1230),fill=PALETTE["accent"])
    d.text((64,1255),"O CORVO INVESTIGADOR",font=face(27,True),fill=PALETTE["text"])
    d.text((944,1255),f"{index:02}/{total:02}",font=face(24,True),fill=PALETTE["text"])
    return im.convert("RGB")

def main():
    p=argparse.ArgumentParser();p.add_argument("spec");p.add_argument("output");p.add_argument("--logo");a=p.parse_args()
    spec=json.loads(Path(a.spec).read_text(encoding="utf-8"))
    slides=spec["slides"]
    if len(slides)!=5 or not all(all(k in s for k in ("title","body","section")) for s in slides):
        raise ValueError("Exactly five complete slides required")
    if a.logo and not Path(a.logo).is_file():raise FileNotFoundError(a.logo)
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True);assets=[]
    for i,s in enumerate(slides,1):
        path=out/f"slide{i}.png";renderer=render_photo_slide if spec.get("style")=="photo_editorial" else render_slide;renderer(s,i,5,a.logo).save(path,optimize=True)
        with Image.open(path) as chk:
            assert chk.format=="PNG" and chk.size==(W,H)
        assets.append({"file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"size":[W,H]})
    (out/"caption.txt").write_text(spec["caption"],encoding="utf-8")
    (out/"manifest.json").write_text(json.dumps({"articleId":spec["articleId"],"status":"RENDERED_NEEDS_EDITORIAL_REVIEW","style":spec.get("style","classic"),"assets":assets,"palette":PALETTE,"sources":spec.get("sources",[]),"photoCredits":spec.get("photoCredits",[])},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":"RENDERED_NEEDS_EDITORIAL_REVIEW","assets":len(assets)}))
if __name__=="__main__":main()
