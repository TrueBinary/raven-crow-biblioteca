"""Raven Crow visual standard: reference-style editorial carousel, no publishing side effects."""
import argparse, json, hashlib, math, random, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
W,H=1080,1350
RED="#E42E3B"; WHITE="#F6F4F0"; DARK="#101014"; MUTED="#D6D0D0"
FONT=Path("C:/Windows/Fonts")
def font(size,heavy=False):
    for name in (["impact.ttf","arialbd.ttf"] if heavy else ["arial.ttf","segoeui.ttf"]):
        p=FONT/name
        if p.exists(): return ImageFont.truetype(str(p),size)
    return ImageFont.load_default()
def wrap(d,s,f,maxw):
    result=[]
    for p in s.split("\n"):
        cur=""
        for word in p.split():
            t=(cur+" "+word).strip()
            if cur and d.textbbox((0,0),t,font=f)[2]>maxw:
                result.append(cur);cur=word
            else:cur=t
        if cur:result.append(cur)
    return result
def title(d,s,y,max_height,accent=True,x=58,width=960,initial=128):
    s=s.upper().strip()
    for size in range(initial,46,-4):
        f=font(size,True);ls=wrap(d,s,f,width);step=int(size*.99)
        if len(ls)*step<=max_height:break
    if len(ls)*step>max_height:raise ValueError("headline overflow: "+s)
    for i,line in enumerate(ls):
        if accent and len(ls)==1 and " " in line:
            # Single-line headline: only the decisive last word is red.
            prefix,last=line.rsplit(" ",1)
            prefix+=" "
            d.text((x,y+i*step),prefix,font=f,fill=WHITE)
            d.text((x+d.textlength(prefix,font=f),y+i*step),last,font=f,fill=RED)
        else:
            color=RED if accent and i==len(ls)-1 else WHITE
            d.text((x,y+i*step),line,font=f,fill=color,stroke_width=0)
    return y+len(ls)*step
def body(d,s,y,limit,fontsize=45,x=62,width=935):
    for sz in range(fontsize,27,-2):
        f=font(sz);ls=wrap(d,s,f,width)
        if y+len(ls)*int(sz*1.27)<=limit:break
    if y+len(ls)*int(sz*1.27)>limit:raise ValueError("body overflow")
    for line in ls:
        d.text((x,y),line,font=f,fill=WHITE);y+=int(sz*1.27)
    return y
def base(logo,idx,total,date):
    im=Image.new("RGB",(W,H),DARK);d=ImageDraw.Draw(im)
    rng=random.Random(331+idx)
    for _ in range(19000):
        x=rng.randrange(W);y=rng.randrange(H)
        v=rng.choice(["#151518","#17171B","#1B1A1D"])
        d.point((x,y),fill=v)
    d.rectangle((0,0,20,H),fill=RED)
    d.rectangle((58,65,92,80),fill=RED)
    d.text((110,45),"RAVEN CROW",font=font(42,True),fill=WHITE)
    d.line((58,112,785,112),fill="#65222A",width=3)
    if logo:
        d.ellipse((870,5,1060,195),outline="#8D2432",width=4)
        pic=Image.open(logo).convert("RGBA")
        bounds=pic.getchannel("A").getbbox()
        if bounds:pic=pic.crop(bounds)
        pic=pic.resize((int(pic.width*160/pic.height),160),Image.Resampling.LANCZOS)
        im.paste(pic,(W-48-pic.width,12),pic)
    d.line((58,1250,1025,1250),fill="#69202B",width=2)
    d.text((58,1274),"O CORVO INVESTIGADOR  /  "+date,font=font(22),fill=WHITE)
    d.text((920,1270),f"{idx:02}/{total:02}",font=font(29,True),fill=RED)
    return im,d
def photo_strip(im,image,y=825,bottom=1235):
    src=Image.open(image).convert("RGB")
    if min(src.size)<640:raise ValueError("Photo too small")
    h=bottom-y
    scale=max(W/src.width,h/src.height)
    src=src.resize((math.ceil(src.width*scale),math.ceil(src.height*scale)),Image.Resampling.LANCZOS)
    left=(src.width-W)//2;top=(src.height-h)//2
    src=src.crop((left,top,left+W,top+h))
    src=ImageEnhance.Color(src).enhance(.24)
    src=ImageEnhance.Contrast(src).enhance(1.18)
    layer=Image.new("RGBA",src.size,(0,0,0,0));dr=ImageDraw.Draw(layer)
    for yy in range(h):
        alpha=185 if yy<85 else max(25,185-int((yy-85)*.65))
        dr.line((0,yy,W,yy),fill=(9,9,13,alpha))
    src=Image.alpha_composite(src.convert("RGBA"),layer).convert("RGB")
    im.paste(src,(0,y))
def editorial_beats(text):
    """Keep complete sentences intact; never cut slide copy into arbitrary thirds."""
    sentences=[part.strip() for part in re.split(r"(?<=[.!?])\s+",text.strip()) if part.strip()]
    if len(sentences)<=3:return sentences
    return sentences[:2]+[" ".join(sentences[2:])]

def slide_points(slide):
    """Up to three editorial beats; the supplied reference uses three icon rows."""
    if "points" not in slide:
        return [{"text":text,"icon":name} for text,name in zip(editorial_beats(slide.get("body","")),("package","factory","handshake"))]
    points=slide["points"]
    if not isinstance(points,list) or not 1<=len(points)<=3:
        raise ValueError("Use one to three meaningful points, not arbitrary chunks")
    for point in points:
        if not isinstance(point,dict) or not str(point.get("text","")).strip():
            raise ValueError("Each point needs a nonempty text")
    return points

def line_icon(d,kind,x,y):
    """Simple original monoline pictograms, like the Mercosul/EFTA reference."""
    color=WHITE
    if kind=="package":
        d.polygon([(x+18,y+25),(x+52,y+10),(x+86,y+25),(x+52,y+41)],outline=color,width=4)
        d.line((x+18,y+25,x+18,y+78,x+52,y+95,x+86,y+78,x+86,y+25),fill=color,width=4)
        d.line((x+52,y+41,x+52,y+95),fill=color,width=4)
    elif kind=="factory":
        d.line((x+14,y+85,x+14,y+47,x+40,y+66,x+40,y+47,x+65,y+65,x+65,y+37,x+91,y+37,x+91,y+85,x+14,y+85),fill=color,width=4)
        d.line((x+72,y+37,x+72,y+15,x+86,y+15,x+86,y+37),fill=color,width=4)
        for dx in (31,50,72):
            d.rectangle((x+dx,y+71,x+dx+9,y+80),outline=color,width=2)
    elif kind=="handshake":
        d.line((x+8,y+47,x+28,y+23,x+49,y+43,x+60,y+33,x+91,y+54),fill=color,width=5)
        d.line((x+8,y+47,x+25,y+72,x+39,y+60,x+62,y+82,x+91,y+54),fill=color,width=5)
        d.line((x+35,y+51,x+67,y+74),fill=color,width=4)
        d.line((x+29,y+61,x+54,y+82),fill=color,width=4)
    else:
        d.ellipse((x+18,y+18,x+88,y+88),outline=color,width=4)
        d.line((x+34,y+54,x+48,y+68,x+74,y+38),fill=color,width=5)

def render(slide,idx,total,logo,date):
    im,d=base(logo,idx,total,date)
    section=slide.get("section","RAVEN CROW").upper()
    text=slide["title"];content=slide.get("body","")
    if idx==1:
        d.rounded_rectangle((58,157,790,215),radius=9,fill="#6D2029")
        d.text((78,169),section[:39],font=font(29,True),fill=WHITE)
        end=title(d,text,265,420,initial=137)
        d.rectangle((58,end+18,335,end+32),fill=RED)
        body(d,content,end+58,830,fontsize=37)
        if slide.get("image"):
            photo_strip(im,slide["image"],y=max(725,end+155))
        else:
            # No unrelated stock image or generic presentation card as a substitute.
            # Keep the same bold documentary cover grid, without inventing a photo.
            d.rectangle((58,867,1024,1188),outline="#6E252E",width=3)
            d.rectangle((58,867,76,1188),fill=RED)
            d.text((110,916),"O CORVO",font=font(100,True),fill=WHITE)
            d.text((110,1020),"INVESTIGADOR",font=font(100,True),fill=RED)
            d.line((110,1145,905,1145),fill=RED,width=6)
        # re-add footer over the photo
        d=ImageDraw.Draw(im)
        d.rectangle((0,1237,W,1350),fill=DARK)
        d.line((58,1250,1025,1250),fill="#69202B",width=2)
        d.text((58,1274),"O CORVO INVESTIGADOR  /  "+date,font=font(22),fill=WHITE)
        d.text((920,1270),f"{idx:02}/{total:02}",font=font(29,True),fill=RED)
    else:
        # The image reference has NO redundant category label on interiors.
        end=title(d,text,242,410,initial=120)
        d.rectangle((58,end+18,300,end+29),fill=RED)
        if idx==total:
            y=body(d,content,end+75,920,fontsize=52)
            box_y=max(940,y+70)
            if box_y>=1080:raise ValueError("CTA has no safe vertical space")
            d.rounded_rectangle((58,box_y,1024,1160),radius=10,fill=RED)
            call1=slide.get("cta1","LEIA A ANÁLISE COMPLETA").upper()
            call2=slide.get("cta2","NA COLUNA DO CORVO").upper()
            for sz in range(53,31,-2):
                if d.textbbox((0,0),call1,font=font(sz,True))[2]<815:break
            d.text((88,box_y+35),call1,font=font(sz,True),fill=WHITE)
            d.text((88,box_y+102),call2,font=font(38,True),fill=WHITE)
            # White forward arrow is a graphic element, not a fake clickable button.
            d.line((947,box_y+104,991,box_y+104),fill=WHITE,width=7)
            d.line((975,box_y+88,991,box_y+104,975,box_y+120),fill=WHITE,width=7)
        else:
            # Mercosul/EFTA: real editorial beats (never split by number of words).
            points=slide_points(slide)
            row_start=max(end+70,560)
            row_step=min(232,(1185-row_start)//max(1,len(points)))
            if row_step<142:raise ValueError("Headline leaves no space for interior points")
            for j,point in enumerate(points):
                y=row_start+j*row_step
                d.rounded_rectangle((64,y,180,y+114),radius=9,outline="#912933",width=4)
                line_icon(d,point.get("icon",("package","factory","handshake")[j]),70,y+6)
                body(d,point["text"],y+8,y+row_step-22,fontsize=43,x=212,width=805)
                d.line((62,y+row_step-16,1022,y+row_step-16),fill="#64202B",width=2)
    return im
def main():
    ap=argparse.ArgumentParser();ap.add_argument("spec");ap.add_argument("out");ap.add_argument("--logo",required=True);ap.add_argument("--date",default="03 NOV 2026");a=ap.parse_args()
    spec=json.loads(Path(a.spec).read_text(encoding="utf-8"))
    slides=spec["slides"]
    if len(slides)!=5:raise ValueError("Five slides required")
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    assets=[]
    for i,slide in enumerate(slides,1):
        im=render(slide,i,5,a.logo,a.date)
        p=out/f"slide{i}.png";im.save(p,optimize=True)
        with Image.open(p) as check:
            if check.size!=(W,H):raise ValueError("invalid size")
        assets.append({"file":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"size":[W,H]})
    (out/"caption.txt").write_text(spec["caption"],encoding="utf-8")
    (out/"manifest.json").write_text(json.dumps({"articleId":spec["articleId"],"style":"raven_reference_v2","designProfile":"mercosul_efta_2026_11_02_locked","status":"RENDERED_NEEDS_QA","visualQa":{"cover":False,"interior":False,"cta":False},"httpsVerified":False,"assets":assets,"sources":spec.get("sources",[]),"photoCredits":spec.get("photoCredits",[])},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"articleId":spec["articleId"],"count":len(assets),"status":"RENDERED_NEEDS_QA"}))
if __name__=="__main__":main()
