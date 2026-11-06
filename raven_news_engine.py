"""Raven Crow single-photo editorial renderer. No publishing side effects."""
import math, argparse, json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
W,H=1080,1350
RED='#e62933'; WHITE='#ffffff'
def overlap(a,b):
 return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
def score_crop(crop,faces,objects,text_zones=()):
 area=lambda r:max(1,(r[2]-r[0])*(r[3]-r[1]))
 # Hard constraints: no face or protected object may be clipped.
 for r in faces:
  if overlap(crop,r)<area(r)*.999:return float('inf')
 for r in objects:
  if overlap(crop,r)<area(r)*.999:return float('inf')
 # Penalties R,O,T,E; hard constraints make R and O zero for valid crops.
 R=sum(1-overlap(crop,r)/area(r) for r in faces)
 O=sum(1-overlap(crop,r)/area(r) for r in objects)
 T=sum(overlap(crop,r)/area(r) for r in text_zones)
 focus=faces or objects
 if focus:
  cx=sum((r[0]+r[2])/2 for r in focus)/len(focus)
  cy=sum((r[1]+r[3])/2 for r in focus)/len(focus)
  E=(abs((crop[0]+crop[2])/2-cx)/(crop[2]-crop[0])+abs((crop[1]+crop[3])/2-cy)/(crop[3]-crop[1]))/2
 else:E=0
 return 5*R+4*O+3*T+2*E
def choose_crop(source_size,target_size,faces,objects):
 sw,sh=source_size;tw,th=target_size
 aspect=tw/th
 cw=min(sw,sh*aspect);ch=cw/aspect
 if ch>sh:ch=sh;cw=ch*aspect
 if cw<1 or ch<1:raise ValueError('Invalid image dimensions')
 best=None
 for ix in range(21):
  for iy in range(21):
   x=(sw-cw)*ix/20;y=(sh-ch)*iy/20
   r=(x,y,x+cw,y+ch)
   score=score_crop(r,faces,objects)
   if math.isfinite(score) and (best is None or score<best[1]):best=(r,score)
 if best is None:raise ValueError('No safe crop: protected subjects would be clipped')
 return best
def font(sz,bold=True):
 p=Path('C:/Windows/Fonts')/('impact.ttf' if bold else 'arial.ttf')
 if p.exists():return ImageFont.truetype(str(p),sz)
 return ImageFont.load_default()
def layout_headline(headline,width,maxheight):
 d=ImageDraw.Draw(Image.new('RGB',(10,10)))
 for sz in range(95,35,-2):
  f=font(sz);lines=[];line=''
  for word in headline.upper().split():
   test=(line+' '+word).strip()
   if line and d.textlength(test,font=f)>width:lines.append(line);line=word
   else:line=test
  if line:lines.append(line)
  if lines and max(d.textlength(x,font=f) for x in lines)<=width and len(lines)*sz*1.03<=maxheight:return lines,sz
 raise ValueError('Headline too long for template; rewrite headline')
def render_news(image,headline,summary,faces,objects,logo):
 if faces is None or objects is None:raise ValueError('Protected-region detection or review is required')
 if image.width<800 or image.height<600:raise ValueError('Image resolution insufficient')
 im=Image.new('RGB',(W,H),'#0d0d10')
 photo_h=865
 crop,_=choose_crop(image.size,(W,photo_h),faces,objects)
 photo=image.convert('RGB').crop(tuple(round(v) for v in crop)).resize((W,photo_h),Image.Resampling.LANCZOS)
 im.paste(photo,(0,0))
 overlay=Image.new('RGBA',(W,H),(0,0,0,0));od=ImageDraw.Draw(overlay)
 # Gradient starts below the subject-priority region; no category or photo credit.
 for y in range(635,1040):
  alpha=int(min(255,max(0,(y-635)/260*255)))
  od.line((0,y,W,y),fill=(8,8,12,alpha))
 od.rectangle((0,1040,W,H),fill=(8,8,12,255))
 im=Image.alpha_composite(im.convert('RGBA'),overlay)
 d=ImageDraw.Draw(im)
 if logo:
  pic=Image.open(logo).convert('RGBA')
  box=pic.getchannel('A').getbbox()
  if box:pic=pic.crop(box)
  pic.thumbnail((225,100),Image.Resampling.LANCZOS)
  im.alpha_composite(pic,(32,23))
  d=ImageDraw.Draw(im)
 else:d.text((35,30),'RAVEN CROW',font=font(52),fill=WHITE)
 d.rectangle((285,32,291,95),fill=RED)
 d.text((312,42),'NOTÍCIAS',font=font(35,False),fill=WHITE)
 lines,sz=layout_headline(headline,1010,345)
 y=850
 for i,line in enumerate(lines):
  color=RED if i==len(lines)-1 else WHITE
  d.text((35,y),line,font=font(sz),fill=color,stroke_width=1,stroke_fill='#161619')
  y+=int(sz*1.03)
 if summary:
  sf=font(29,False)
  words=summary.split();ls=[];line=''
  for word in words:
   trial=(line+' '+word).strip()
   if line and d.textlength(trial,font=sf)>945:ls.append(line);line=word
   else:line=trial
  if line:ls.append(line)
  if len(ls)>2:raise ValueError('Summary too long: shorten copy')
  sy=max(y+22,1215)
  if sy+len(ls)*37>1330:raise ValueError('Summary overflow')
  d.rectangle((35,sy-2,42,sy+len(ls)*37),fill=RED)
  for l in ls:d.text((62,sy),l,font=sf,fill=WHITE);sy+=37
 return im.convert('RGB')
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--image',required=True);p.add_argument('--headline',required=True);p.add_argument('--summary',default='')
 p.add_argument('--regions',required=True,help='JSON with faces and objects bounding boxes in original image pixels')
 p.add_argument('--logo');p.add_argument('--output',required=True)
 a=p.parse_args()
 regions=json.loads(Path(a.regions).read_text(encoding='utf8'))
 if 'faces' not in regions or 'objects' not in regions:raise ValueError('Regions must be explicitly verified')
 im=render_news(Image.open(a.image),a.headline,a.summary,regions['faces'],regions['objects'],a.logo)
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True);im.save(dest,quality=92)
 print(json.dumps({'status':'rendered','output':str(dest),'size':list(im.size),'format':'single-photo'}))
if __name__=='__main__':main()
