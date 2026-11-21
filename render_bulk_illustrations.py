"""Original product-type illustrations for small craft resale lots.

Generates three neutral white-background images from scratch. No copied supplier art.
Images are renderings, not photographs of the seller's physical stock.
"""
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path
import math, random

SIZE=(1200,900)
OUT=Path("assets")
OUT.mkdir(exist_ok=True)
random.seed(2811)

def canvas():
    im=Image.new("RGB",SIZE)
    pix=im.load()
    for y in range(SIZE[1]):
        base=255-round(y/900*8)
        for x in range(SIZE[0]):
            d=round(abs(x-600)/600*3)
            pix[x,y]=(max(0,base-d),max(0,base-d),max(0,base-d))
    return im

def arc_ring(draw,x,y,r,w=5,gap=0.36):
    # Metallic 3D open jump ring with a deliberately small opening.
    start=math.degrees(gap/2)+32
    end=start+360-math.degrees(gap)
    b=(x-r,y-r,x+r,y+r)
    draw.arc((x-r+2,y-r+3,x+r+2,y+r+3),start,end,fill=(163,168,173),width=w+3)
    draw.arc(b,start,end,fill=(119,129,139),width=w)
    draw.arc((x-r+1,y-r+1,x+r-1,y+r-1),start,end,fill=(220,224,226),width=max(2,w-2))
    draw.arc((x-r+2,y-r+2,x+r-2,y+r-2),start+45,start+150,fill=(250,250,250),width=2)

def rings():
    im=canvas()
    layer=Image.new("RGBA",SIZE,(0,0,0,0))
    sh=ImageDraw.Draw(layer)
    for i in range(100):
        x=random.randint(115,1030)
        y=random.randint(180,735)
        r=random.randint(18,24)
        sh.ellipse((x-r+8,y-r+11,x+r+8,y+r+11),fill=(45,54,60,22))
    im=Image.alpha_composite(im.convert("RGBA"),layer.filter(ImageFilter.GaussianBlur(8)))
    d=ImageDraw.Draw(im)
    for i in range(100):
        x=random.randint(120,1040)
        y=random.randint(188,740)
        r=random.randint(18,24)
        arc_ring(d,x,y,r,5,0.33)
    im.convert("RGB").save(OUT/"bulk-6mm-jump-rings.jpg",quality=92,optimize=True)

def grip_bags():
    im=canvas().convert("RGBA")
    shadow=Image.new("RGBA",SIZE,(0,0,0,0))
    sh=ImageDraw.Draw(shadow)
    dims=[(120,190),(145,180),(158,225),(180,245),(200,275)]
    centers=[(157,460),(380,456),(600,449),(828,435),(1060,422)]
    for (w,h),(cx,cy) in zip(dims,centers):
        for i in range(5):
            x=cx-w//2+i*4
            y=cy-h//2-i*5
            sh.rounded_rectangle((x+12,y+12,x+w+12,y+h+12),radius=8,fill=(0,0,0,24))
    im=Image.alpha_composite(im,shadow.filter(ImageFilter.GaussianBlur(12)))
    overlay=Image.new("RGBA",SIZE,(0,0,0,0))
    d=ImageDraw.Draw(overlay)
    for (w,h),(cx,cy) in zip(dims,centers):
        for i in range(6):
            x=cx-w//2+(5-i)*3
            y=cy-h//2-(5-i)*5
            # Pale transparent flexible PE bags with twin press-seal ridges.
            d.rounded_rectangle((x,y,x+w,y+h),radius=7,fill=(240,246,250,40),outline=(132,153,166,100),width=3)
            d.line((x+3,y+19,x+w-3,y+19),fill=(93,125,145,115),width=3)
            d.line((x+3,y+25,x+w-3,y+25),fill=(209,225,235,160),width=3)
            d.line((x+14,y+36,x+14,y+h-14),fill=(255,255,255,150),width=5)
            d.line((x+w-18,y+40,x+w-18,y+h-12),fill=(173,200,214,64),width=2)
    im=Image.alpha_composite(im,overlay)
    im.convert("RGB").save(OUT/"bulk-grip-seal-bags.jpg",quality=94,optimize=True)

def tags():
    im=canvas().convert("RGBA")
    shadow=Image.new("RGBA",SIZE,(0,0,0,0))
    s=ImageDraw.Draw(shadow)
    colors=[(172,123,78),(245,243,239),(54,54,57)]
    xs=[300,600,900]
    for x in xs:
        s.ellipse((x-145,295,x+145,635),fill=(0,0,0,45))
    im=Image.alpha_composite(im,shadow.filter(ImageFilter.GaussianBlur(20)))
    layer=Image.new("RGBA",SIZE,(0,0,0,0))
    d=ImageDraw.Draw(layer)
    for x,color in zip(xs,colors):
        # Three stacks of circular tags; every round tag has a punched hole.
        for k in range(12):
            y=490-k*7
            d.ellipse((x-137,y-137,x+137,y+137),fill=(*color,255),outline=(120,119,112,160),width=2)
            d.ellipse((x-12,y-109,x+12,y-85),fill=(243,241,236,255),outline=(121,121,118,150),width=2)
        y=490-11*7
        d.arc((x-135,y-135,x+135,y+135),205,330,fill=(255,255,255,75),width=3)
    # Realistic natural twine loop at front right, independent of the tags.
    for j in range(4):
        b=(864+j*4,668+j*2,1096+j*2,811+j)
        d.arc(b,0,335,fill=(151+min(40,j*5),122+min(40,j*5),82+min(40,j*5),220),width=4)
    im=Image.alpha_composite(im,layer)
    im.convert("RGB").save(OUT/"bulk-round-kraft-tags.jpg",quality=94,optimize=True)

if __name__=="__main__":
    rings();grip_bags();tags()
    for f in sorted(OUT.glob("bulk-*.jpg")):
        print(f, f.stat().st_size, "bytes")
