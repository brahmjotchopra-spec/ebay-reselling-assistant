"""Generate an original text-free illustration of 50 generic silver split rings.
This depicts a generic key ring pack; replace with seller's own photographs when available.
"""
from PIL import Image, ImageDraw
from pathlib import Path
W=1000
im=Image.new("RGB",(W,W),"white")
d=ImageDraw.Draw(im)
def oval(cx,cy,rx,ry):
    box=(int(cx-rx),int(cy-ry),int(cx+rx),int(cy+ry))
    d.ellipse(box,outline=(95,104,111),width=12)
    d.ellipse((box[0]+3,box[1]+3,box[2]-3,box[3]-3),outline=(225,229,232),width=5)
    d.ellipse((box[0]+5,box[1]+5,box[2]-5,box[3]-5),outline=(251,253,253),width=2)
    x=int(cx+rx*.86); y=int(cy-ry*.50)
    d.line((x-1,y-4,x+3,y+2),fill=(90,98,105),width=2)
for cx,cy in [(230,590),(500,580),(770,590)]:
    d.ellipse((cx-115,cy+25,cx+120,cy+60),fill=(247,247,247))
    for n in range(15):oval(cx,cy-13*n,106,42)
for cx,cy in [(160,827),(335,858),(505,828),(665,862),(838,827)]:
    oval(cx,cy,95,73)
Path("assets").mkdir(exist_ok=True)
im.save("assets/keyrings-50.jpg","JPEG",quality=94,optimize=True)
print("Original 1000x1000 product illustration generated.")
