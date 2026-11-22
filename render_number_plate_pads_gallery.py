"""Render six ORIGINAL numbered eBay listing illustrations for 10 vehicle plate pads.
Source: user-supplied pictures 22 Nov 2026: red release liner, black foam,
nominal 90 x 20 x 2 mm. Illustrations, not photographs of actual stock.
Do not use competitor imagery, logos, brand claims or misleading 50-pack count.
"""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SIZE=1200
OUT=Path("assets/number-plate-pads")
OUT.mkdir(parents=True,exist_ok=True)
WHITE=(255,255,255); INK=(24,33,44); GREY=(96,108,119)
RED=(202,38,45); RED2=(239,65,69); DEEP=(145,19,29)
PALE=(251,243,243); LINE=(230,235,241)

def font(n,bold=False):
    name="DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for path in ("/usr/share/fonts/truetype/dejavu/"+name,"/usr/share/fonts/truetype/liberation2/"+name):
        if Path(path).exists(): return ImageFont.truetype(path,n)
    return ImageFont.load_default()

def text(d,xy,t,size=36,bold=False,color=INK,anchor=None):
    d.text(xy,t,font=font(size,bold),fill=color,anchor=anchor)

def base():
    im=Image.new("RGB",(SIZE,SIZE),WHITE)
    return im,ImageDraw.Draw(im)

def top(d,subtitle):
    d.rounded_rectangle((60,48,1140,61),radius=7,fill=RED)
    text(d,(62,92),subtitle,30,False,GREY)

def footer(d,s):
    d.line((60,1120,1140,1120),fill=LINE,width=3)
    text(d,(62,1143),s,21,False,GREY)

def make_pad(w=470,h=102,peel=False):
    # Actual aspect ratio 4.5:1. Black foam beneath removable red liner.
    l=Image.new("RGBA",(w+20,h+30),(0,0,0,0))
    d=ImageDraw.Draw(l)
    d.rounded_rectangle((9,16,w+8,h+25),radius=9,fill=(39,42,49,255))
    d.rounded_rectangle((0,0,w,h),radius=7,fill=RED)
    for x in range(8,w-10,9):
        d.line((x,8,x,h-9),fill=(222,62,66,170),width=2)
        d.line((x+3,8,x+3,h-9),fill=(151,31,37,95),width=1)
    d.line((8,6,w-8,6),fill=(249,127,126,175),width=3)
    if peel:
        # Depict red liner lifted, exposing black adhesive foam.
        d.polygon([(w-105,h),(w-16,h),(w-16,4),(w-85,18)],fill=(27,30,35,255))
        d.polygon([(w-103,h),(w-14,25),(w-14,0),(w-102,15)],fill=(249,113,114,255))
    return l

def paste_pad(im,x,y,w=470,h=102,angle=0,peel=False):
    pad=make_pad(w,h,peel)
    if angle:
        pad=pad.rotate(angle,Image.Resampling.BICUBIC,expand=True)
    im.paste(pad,(int(x),int(y)),pad)

def card(d,x1,y1,x2,y2,fill=WHITE,r=28):
    d.rounded_rectangle((x1,y1,x2,y2),radius=r,fill=fill,outline=LINE,width=3)

# 01 main — plain product, exactly 10 pads in two sets of five
im,d=base()
for col,x in enumerate((110,650)):
    for row in range(5):
        paste_pad(im,x,210+row*142,w=430,h=92,angle=0,peel=(col==1 and row==4))
d=ImageDraw.Draw(im)
text(d,(600,110),"10 DOUBLE-SIDED FOAM PADS",48,True,INK,"mm")
footer(d,"Product illustration | 10 red-release-liner adhesive strips")
im.save(OUT/"01-main-10-pads.jpg",quality=94,optimize=True)

# 02 premium informational image
im,d=base()
d.rounded_rectangle((0,0,1200,330),radius=0,fill=(29,35,44))
text(d,(70,95),"10 NUMBER PLATE",56,True,WHITE)
text(d,(70,172),"STICKY PADS",76,True,WHITE)
text(d,(73,270),"Pre-cut • Double-sided • Black foam",28,False,(221,226,235))
paste_pad(im,205,435,w=770,h=175,peel=True)
d=ImageDraw.Draw(im)
card(d,100,730,1100,1045,PALE)
text(d,(600,800),"10",122,True,RED,"mm")
text(d,(600,937),"PADS IN THIS LISTING",41,True,INK,"mm")
footer(d,"Supplied: 10 individual pieces | No number plate included")
im.save(OUT/"02-quantity-10.jpg",quality=94,optimize=True)

# 03 dimensions, accurate aspect and foam layering
im,d=base(); top(d,"DIMENSIONS")
text(d,(60,152),"Pre-cut adhesive strips",56,True)
paste_pad(im,160,370,w=850,h=188,peel=True)
d=ImageDraw.Draw(im)
# horizontal arrow
d.line((162,660,1010,660),fill=INK,width=5)
d.polygon([(162,660),(188,648),(188,672)],fill=INK)
d.polygon([(1010,660),(984,648),(984,672)],fill=INK)
text(d,(586,690),"90 mm length",40,True,INK,"mt")
# width arrow
d.line((1040,373,1040,558),fill=INK,width=5)
d.polygon([(1040,373),(1028,400),(1052,400)],fill=INK)
d.polygon([(1040,558),(1028,531),(1052,531)],fill=INK)
text(d,(910,585),"20 mm wide",29,True,INK)
card(d,95,810,1105,1030,(250,250,252))
text(d,(150,850),"Thickness",36,False,GREY)
text(d,(152,915),"2 mm",67,True,RED)
text(d,(515,852),"Red removable film",31,True)
text(d,(515,909),"Black double-sided foam beneath",25,False,GREY)
footer(d,"Nominal dimensions per pad: 90 × 20 × 2 mm")
im.save(OUT/"03-exact-dimensions.jpg",quality=94,optimize=True)

# 04 liner detail
im,d=base(); top(d,"HOW THE PAD WORKS")
text(d,(62,165),"Red peel-off backing",53,True)
text(d,(62,239),"over black foam adhesive",38,False,GREY)
paste_pad(im,120,400,w=940,h=209,peel=True)
d=ImageDraw.Draw(im)
card(d,120,790,1080,1030,(249,251,253))
d.ellipse((163,843,209,889),fill=RED)
text(d,(188,867),"1",29,True,WHITE,"mm")
text(d,(239,851),"Remove the red protective film",32,True)
d.ellipse((163,933,209,979),fill=RED)
text(d,(188,957),"2",29,True,WHITE,"mm")
text(d,(239,943),"Press the adhesive onto a clean, dry surface",27)
footer(d,"Illustration shows the release liner lifted; no tools included")
im.save(OUT/"04-peel-and-stick-detail.jpg",quality=94,optimize=True)

# 05 number plate mounting behind blank plate
im,d=base();top(d,"VEHICLE NUMBER PLATE USE")
text(d,(62,157),"Fix without drilling",54,True)
text(d,(63,225),"Use on suitable clean, dry surfaces",28,False,GREY)
# blank illustrative registration plate
d.rounded_rectangle((110,430,1090,735),radius=19,fill=(243,245,249),outline=(71,82,96),width=10)
d.rounded_rectangle((132,454,1068,710),radius=11,outline=(177,184,194),width=4)
for x in (215,430,645,860):
    d.rounded_rectangle((x,520,x+63,655),radius=8,fill=(45,48,56))
    d.rounded_rectangle((x+4,520,x+59,644),radius=6,fill=RED)
    for yy in range(529,638,9):d.line((x+8,yy,x+53,yy),fill=RED2,width=2)
text(d,(600,794),"Illustrative placement on reverse side",31,False,GREY,"mm")
card(d,120,881,1080,1020,PALE)
text(d,(600,945),"10 strips supplied — arrange to suit the plate",27,True,INK,"mm")
footer(d,"No number plate or vehicle supplied • adhesive suitability varies")
im.save(OUT/"05-number-plate-example.jpg",quality=94,optimize=True)

# 06 close-up and pack contents
im,d=base();top(d,"PACK CONTENTS")
text(d,(62,170),"10 Red-Backed Adhesive Strips",47,True)
for i in range(5):
    paste_pad(im,90,333+i*124,w=455,h=92)
    paste_pad(im,630,333+i*124,w=455,h=92)
d=ImageDraw.Draw(im)
card(d,150,1004,1050,1093,(248,249,250),16)
text(d,(600,1045),"Double-sided foam  |  90 × 20 × 2 mm",29,True,INK,"mm")
im.save(OUT/"06-pack-contents.jpg",quality=94,optimize=True)
for p in OUT.glob("*.jpg"):
    print("GALLERY_IMAGE",p,p.stat().st_size)
