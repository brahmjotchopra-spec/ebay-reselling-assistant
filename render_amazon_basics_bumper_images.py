"""Produce original, illustrative eBay imagery for the 300-piece mixed bumper set.
These are vector-like illustrations, not photographs of physical stock.
Do not modify or misrepresent any manufacturer photos.
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math
ROOT=Path("assets")
ROOT.mkdir(exist_ok=True)
W=1400
INK=(25,37,50)
ORANGE=(238,108,26)
def font(sz,bold=False):
    name="/usr/share/fonts/truetype/dejavu/DejaVuSans"+("-Bold" if bold else "")+".ttf"
    return ImageFont.truetype(name,sz)
def backdrop():
    im=Image.new("RGB",(W,W),(250,251,252));d=ImageDraw.Draw(im)
    d.rounded_rectangle((28,28,W-28,W-28),radius=36,fill="white",outline=(225,231,237),width=3)
    return im,d
def single_pad(d,x,y,r,typ):
    if typ=="square":
        rr=(x-r,y-r,x+r,y+r)
        d.rounded_rectangle((rr[0]+2,rr[1]+6,rr[2]+2,rr[3]+6),radius=max(2,r//7),fill=(222,231,235))
        d.rounded_rectangle(rr,radius=max(2,r//7),fill=(237,243,248),outline=(173,191,205),width=2)
        d.rounded_rectangle((x-r+5,y-r+5,x+r-5,y+r-5),radius=max(2,r//9),outline=(255,255,255),width=3)
    else:
        d.ellipse((x-r+2,y-r+5,x+r+2,y+r+5),fill=(219,230,239))
        d.ellipse((x-r,y-r,x+r,y+r),fill=(232,240,248),outline=(173,194,211),width=2)
        if typ=="high":
            d.ellipse((x-r+3,y-r+3,x+r-3,y+r-3),fill=(218,231,242),outline=(255,255,255),width=3)
        d.arc((x-r+5,y-r+5,x+r-5,y+r-5),195,300,fill=(255,255,255),width=4)
def sheet(d,x,y,w,h,rows,cols,typ):
    d.rounded_rectangle((x+5,y+10,x+w+5,y+h+10),radius=10,fill=(225,231,238))
    d.rounded_rectangle((x,y,x+w,y+h),radius=10,fill=(248,251,253),outline=(213,223,231),width=2)
    cw=w/cols;ch=h/rows;r=int(min(cw,ch)*0.32)
    for a in range(rows):
        for b in range(cols):
            single_pad(d,int(x+(b+.5)*cw),int(y+(a+.5)*ch),r,typ)
def draw_main():
    im,d=backdrop()
    d.text((90,84),"CLEAR SELF-ADHESIVE BUMPER PADS",font=font(43,True),fill=INK)
    d.text((93,142),"Mixed shapes & sizes  •  300 pieces",font=font(29),fill=(85,102,119))
    sheet(d,90,260,710,480,10,10,"round")
    sheet(d,835,260,460,480,10,5,"round")
    sheet(d,90,785,360,250,4,5,"square")
    sheet(d,485,785,360,250,4,5,"square")
    sheet(d,885,785,410,250,5,10,"round")
    sheet(d,165,1072,490,225,5,7,"high")
    sheet(d,715,1072,490,225,5,5,"round")
    im.save(ROOT/"amazon-basics-bumpers-300-main.jpg",quality=89,optimize=True)
def draw_details():
    im,d=backdrop()
    d.text((90,82),"WHAT'S IN THE SET",font=font(53,True),fill=INK)
    d.text((90,159),"300 assorted clear bumper pads",font=font(32),fill=(87,105,119))
    detail=[("Small round",100,"round"),("Medium round",50,"round"),("Square bumper",20,"square"),("Small square",20,"square"),("Flat circular",50,"round"),("Raised domes",35,"high"),("Round pads",25,"round")]
    x0,y0=88,265
    for i,(name,n,typ) in enumerate(detail):
        c=i%2;row=i//2
        x=x0+c*615;y=y0+row*252
        d.rounded_rectangle((x,y,x+572,y+220),radius=22,fill=(248,251,253),outline=(226,232,238),width=2)
        for j in range(6):
            single_pad(d,x+61+(j%3)*70,y+55+(j//3)*73,21,typ)
        d.text((x+258,y+54),str(n)+" pcs",font=font(37,True),fill=INK)
        d.text((x+258,y+115),name,font=font(23),fill=(87,102,113))
    d.rounded_rectangle((90,1274,1310,1333),radius=18,fill=(255,240,231))
    d.text((172,1286),"Original illustration • Always check actual dimensions",font=font(23),fill=(126,74,42))
    im.save(ROOT/"amazon-basics-bumpers-300-details.jpg",quality=89,optimize=True)
if __name__=="__main__":
    draw_main();draw_details()
    print("Created original illustrative photos: main & count breakdown")
