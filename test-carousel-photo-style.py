import importlib.util,tempfile
from pathlib import Path
from PIL import Image
p=Path(r"D:\CorteFlow\config\raven-carousel-render.py")
s=importlib.util.spec_from_file_location("carousel",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with tempfile.TemporaryDirectory() as t:
 photo=Path(t)/"photo.jpg";Image.new("RGB",(1200,1500),"#767676").save(photo)
 slide={"section":"POLITICA","title":"Manchete com foto em destaque","body":"texto","image":str(photo)}
 img=m.render_photo_slide(slide,1,5)
 assert img.size==(1080,1350)
 print("PASS photo_editorial",img.size)
try:
 m.render_photo_slide({"section":"A","title":"B","body":"C"},1,5)
 raise AssertionError("should reject missing photo")
except ValueError: print("PASS missing image blocked")
