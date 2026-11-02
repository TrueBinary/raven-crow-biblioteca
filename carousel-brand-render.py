"""Raven Crow visual standard: reference-style editorial carousel, no publishing side effects."""
import argparse, json, hashlib, math, random
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
        # Last line carries the brand accent, as in the supplied reference.
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
        if not slide.get("image"):raise ValueError("Cover requires documentary photo")
        photo_strip(im,slide["image"],y=max(725,end+155))
        # re-add footer over the photo
        d=ImageDraw.Draw(im)
        d.rectangle((0,1237,W,1350),fill=DARK)
        d.line((58,1250,1025,1250),fill="#69202B",width=2)
        d.text((58,1274),"O CORVO INVESTIGADOR  /  "+date,font=font(22),fill=WHITE)
        d.text((920,1270),f"{idx:02}/{total:02}",font=font(29,True),fill=RED)
    else:
        d.text((58,173),section[:42],font=font(27,True),fill=RED)
        end=title(d,text,262,390,initial=120)
        d.rectangle((58,end+18,300,end+29),fill=RED)
        if idx==total:
            y=body(d,content,end+75,920,fontsize=52)
            box_y=max(940,y+70)
            d.rounded_rectangle((58,box_y,1024,1160),radius=10,fill="#9B2530")
            d.text((88,box_y+39),"LEIA A ANÁLISE",font=font(58,True),fill=WHITE)
            d.text((88,box_y+106),"NA COLUNA DO CORVO  →",font=font(40,True),fill=WHITE)
        else:
            # Divide the exact source sentence into three editorial reading beats.
            words=content.split()
            cuts=[round(len(words)/3),round(2*len(words)/3)]
            chunks=[" ".join(words[:cuts[0]])," ".join(words[cuts[0]:cuts[1]])," ".join(words[cuts[1]:])]
            row_start=max(end+70,645)
            row_step=min(184,(1190-row_start)//3)
            for j,chunk in enumerate(chunks):
                if not chunk:continue
                y=row_start+j*row_step
                d.rounded_rectangle((60,y,174,y+112),radius=10,outline="#842833",width=4)
                if j==0:
                    d.rectangle((91,y+28,144,y+83),outline=WHITE,width=5)
                elif j==1:
                    d.ellipse((91,y+25,136,y+70),outline=WHITE,width=5)
                    d.line((131,y+70,153,y+92),fill=WHITE,width=5)
                else:
                    d.line((89,y+57,112,y+82,153,y+26),fill=WHITE,width=6)
                body(d,chunk,y+12,y+122,fontsize=43,x=214,width=795)
                d.line((60,y+row_step-18,1025,y+row_step-18),fill="#64202B",width=2)
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
    (out/"manifest.json").write_text(json.dumps({"articleId":spec["articleId"],"style":"raven_reference_v2","status":"RENDERED_NEEDS_QA","assets":assets,"sources":spec.get("sources",[]),"photoCredits":spec.get("photoCredits",[])},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"articleId":spec["articleId"],"count":len(assets),"status":"RENDERED_NEEDS_QA"}))
if __name__=="__main__":main()
