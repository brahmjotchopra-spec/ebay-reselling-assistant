"""Create original plain product-type illustrations for eBay household goods.

Not stock photography. Never copy Amazon seller imagery; descriptive disclosures
are added by the publication script. No overlaid marketing text or watermarks.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
import math,random

OUT=Path("assets")
OUT.mkdir(exist_ok=True)
W,H=1200,900
R=random.Random(11021)

def base():
    im=Image.new("RGB",(W,H),(250,251,251))
    d=ImageDraw.Draw(im)
    for y in range(H):
        a=int(250-y*0.006)
        d.line((0,y,W,y),fill=(a,a,a))
    return im

def shadow(im,rect,radius=35,alpha=45):
    layer=Image.new("RGBA",im.size,(0,0,0,0))
    d=ImageDraw.Draw(layer)
    d.ellipse(rect,fill=(15,23,30,alpha))
    return Image.alpha_composite(im.convert("RGBA"),layer.filter(ImageFilter.GaussianBlur(radius)))

def cloths():
    im=base()
    im=shadow(im,(130,660,1120,785),32,60)
    d=ImageDraw.Draw(im)
    palettes=[(159,183,194),(184,193,182),(199,191,179),(188,184,204)]
    for stack,(cx,c) in enumerate(zip((230,480,730,980),palettes)):
        for n in range(5):
            y=630-n*57
            x=cx-105+(n%2)*5
            fill=tuple(min(252,v+n%3*7) for v in c)
            d.rounded_rectangle((x,y,x+211,y+65),radius=12,fill=fill,outline=(140,148,150),width=3)
            d.line((x+6,y+14,x+202,y+14),fill=tuple(min(250,v+18) for v in fill),width=5)
            d.line((x+14,y+50,x+193,y+50),fill=(127,137,140),width=2)
            for t in range(25):
                tx=x+12+t*7
                d.line((tx,y+21,tx+2,y+43),fill=tuple(max(50,v-12) for v in fill),width=1)
    im.convert("RGB").save(OUT/"household-microfibre-20.jpg",quality=91,optimize=True)
    print("IMAGE household-microfibre-20.jpg", (OUT/"household-microfibre-20.jpg").stat().st_size,flush=True)

def liners():
    im=base()
    im=shadow(im,(255,735,1010,790),24,47)
    d=ImageDraw.Draw(im)
    # Fluted square bowl-shaped parchment sheets in a light brown paper stack.
    for j in range(14):
        delta=14-j*2
        cx,cy=620,615-j*21
        rx,ry=290-delta,165-delta//2
        col=(185+min(j,14)*2,147+min(j,14)*2,105+min(j,14)*2)
        pts=[(cx-rx,cy-ry+35),(cx-rx+40,cy-ry-30),(cx+rx-40,cy-ry-30),(cx+rx,cy-ry+35),
             (cx+rx,cy+ry-25),(cx+rx-55,cy+ry+20),(cx-rx+55,cy+ry+20),(cx-rx,cy+ry-25)]
        d.polygon(pts,fill=col)
        d.line(pts+[pts[0]],fill=(128,93,62),width=3)
        for k in range(16):
            x=cx-rx+25+k*int((2*rx-50)/16)
            d.line((x,cy-ry+3,x+R.randint(-17,17),cy+ry-15),fill=(160,120,79),width=2)
    d.rounded_rectangle((385,330,855,555),radius=20,fill=(207,169,118),outline=(135,103,70),width=4)
    for y in range(352,551,27):
        d.line((407,y,833,y),fill=(227,195,153),width=3)
    im.convert("RGB").save(OUT/"household-air-fryer-liners-100.jpg",quality=91,optimize=True)
    print("IMAGE household-air-fryer-liners-100.jpg", (OUT/"household-air-fryer-liners-100.jpg").stat().st_size,flush=True)

def drains():
    im=base()
    im=shadow(im,(260,725,1030,780),30,40)
    d=ImageDraw.Draw(im)
    # Several overlapping square adhesive mesh filters on a white background.
    for n in range(8):
        x=310+n*46
        y=215+n*49
        d.rounded_rectangle((x,y,x+380,y+310),radius=12,fill=(229,233,234),outline=(172,180,184),width=3)
        d.rectangle((x+22,y+23,x+358,y+287),fill=(244,246,246),outline=(198,202,203),width=2)
        for k in range(0,330,14):
            d.line((x+25+k,y+25,x+25+k,y+284),fill=(183,193,196),width=1)
        for k in range(0,260,14):
            d.line((x+25,y+25+k,x+356,y+25+k),fill=(183,193,196),width=1)
    im.convert("RGB").save(OUT/"household-drain-hair-catchers-100.jpg",quality=91,optimize=True)
    print("IMAGE household-drain-hair-catchers-100.jpg", (OUT/"household-drain-hair-catchers-100.jpg").stat().st_size,flush=True)

if __name__=="__main__":
    cloths();liners();drains()
