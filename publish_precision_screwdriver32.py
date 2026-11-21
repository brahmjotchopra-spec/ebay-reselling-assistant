"""Publish precisely one owned 32-in-1 precision screwdriver kit on eBay UK.

21 Nov 2026: seller explicitly confirms physical stock and supplies six product
gallery screenshots of the grey 32-in-1 case, screwdriver and bits. A matching
isolated product image is used as the basis of the listing photos. This process
never buys supplier stock or changes any unrelated live listing. It refuses to
create a second offer if the existing exact-SKU offer is missing or changed.
"""
import sys, time, json
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from PIL import Image, ImageOps, ImageDraw, ImageFont
from ebay_client import Inventory, DraftError, get_token

# Log only eBay API validation error messages (never auth headers/token values).
def ebay_write(api, method, path, payload=None):
    body=json.dumps(payload).encode() if payload is not None else None
    req=Request("https://api.ebay.com/sell/inventory/v1"+path, data=body,
                method=method, headers=api.headers)
    try:
        with urlopen(req,timeout=25) as resp:
            data=resp.read()
        return json.loads(data) if data else {}
    except HTTPError as exc:
        try:
            content=json.loads(exc.read())
            for err in content.get("errors",[])[:4]:
                print("EBAY FIELD ERROR",method,path,"HTTP",exc.code,
                      "CODE",err.get("errorId"),"MESSAGE",err.get("message"),
                      "PARAMETERS",err.get("parameters"),flush=True)
        except (ValueError,KeyError,TypeError):
            print("EBAY API HTTP ERROR",method,path,exc.code,flush=True)
        raise DraftError("eBay declined "+method+" "+path) from None


SKU="DRAFT-AMZ-PRECISION-SCREW32-1"
CATEGORY="42255"
PRICE="7.49"
TITLE="32 in 1 Precision Screwdriver Set Magnetic Mini Repair Kit Phone Laptop Watch"
DESCRIPTION=(
    "32-in-1 compact manual precision screwdriver kit with removable screwdriver "
    "bits in a grey storage case and a magnetic interchangeable-bit screwdriver "
    "handle, for compatible small repairs. Ideal for suitable watches, glasses, "
    "PCs, phones, laptops, small electronics and hobby work. Bit heads include "
    "common Phillips, slotted, Torx and other precision profiles; always check "
    "the bit and screw compatibility before use. "
    "Includes one compact screwdriver kit (30 assorted bits, handle and extension). "
    "Case dimensions approximately 12.5 x 7 x 3 cm, as shown in the supplier "
    "product specifications; measured packed dimensions may differ. "
    "The gallery uses a matching supplier product image plus an original digital "
    "size guide; no additional loose tools beyond the set are included."
)
SOURCE_URLS=[
    "https://media.adeo.com/mkp/163115c8c3fef6242e75899f42d5654c/media.jpeg?fit=bounds&format=jpg&height=3000&quality=80&width=3000",
    "https://media.adeo.com/mkp/163115c8c3fef6242e75899f42d5654c/media.jpeg",
]
ROOT="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/"
PHOTOS=["precision-screwdriver32-main.jpg","precision-screwdriver32-size.jpg"]
PHOTO_URLS=[ROOT+p for p in PHOTOS]

def jpeg_ok(url):
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; product-image-check/1.0)"})
    with urlopen(req,timeout=20) as r:
        if r.status!=200 or "image" not in r.headers.get("Content-Type",""):
            return False
        return r.read(3)==bytes.fromhex("ffd8ff")

def font(size,bold=False):
    path=("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    return ImageFont.truetype(path,size)

def render():
    image=None
    for url in SOURCE_URLS:
        try:
            req=Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"image/avif,image/webp,image/*,*/*"})
            with urlopen(req,timeout=25) as resp:
                blob=resp.read(10_000_000)
            original=Image.open(BytesIO(blob))
            original.load()
            if min(original.size)<450:
                raise ValueError("Supplier image smaller than 450px")
            image=original.convert("RGB")
            break
        except (HTTPError,URLError,ValueError,OSError):
            continue
    if image is None:
        raise DraftError("Cannot obtain the exact matching supplier photo - no publication")
    out=Path("assets")
    out.mkdir(parents=True,exist_ok=True)
    # Main photo: supplier product shown against white; no app interface or copied banners.
    main=Image.new("RGB",(1200,1200),"white")
    fitted=ImageOps.contain(image,(1100,1100),Image.Resampling.LANCZOS)
    main.paste(fitted,((1200-fitted.width)//2,(1200-fitted.height)//2))
    main.save(out/PHOTOS[0],"JPEG",quality=88,optimize=True,progressive=True)
    # Secondary gallery image is an original simple data/size graphic with the same product.
    poster=Image.new("RGB",(1200,1200),(248,249,250))
    draw=ImageDraw.Draw(poster)
    draw.rectangle((0,0,1200,100),fill=(30,37,47))
    draw.text((65,30),"32-IN-1 PRECISION SCREWDRIVER KIT",font=font(37,True),fill="white")
    small=ImageOps.contain(image,(1070,820),Image.Resampling.LANCZOS)
    poster.paste(small,((1200-small.width)//2,115+(810-small.height)//2))
    draw.line((60,965,1140,965),fill=(210,215,223),width=4)
    draw.text((65,1002),"COMPACT STORAGE CASE",font=font(44,True),fill=(32,40,50))
    draw.text((66,1080),"Approx. 12.5 x 7 x 3 cm  |  Set of 32 tools / parts",font=font(26),fill=(70,78,90))
    poster.save(out/PHOTOS[1],"JPEG",quality=88,optimize=True,progressive=True)
    for p in PHOTOS:
        pic=Image.open(out/p)
        if pic.size!=(1200,1200):
            raise DraftError("Unexpected image dimensions")
        print("GALLERY GENERATED",str(out/p),flush=True)

def prepare():
    for url in PHOTO_URLS:
        for n in range(22):
            try:
                if jpeg_ok(url):
                    print("PUBLIC JPEG READY",url,flush=True)
                    break
            except (HTTPError,URLError,OSError,ValueError):
                pass
            if n==21:
                raise DraftError("Image URL not yet public; refusing publication")
            time.sleep(3)

    api=Inventory(get_token())
    api.check_access()
    offers=api.offers(SKU)
    if len(offers)!=1:
        raise DraftError("Expected exactly one existing screwdriver offer; refuse duplicate")
    offer=api.offer(offers[0]["offerId"])
    item=api.item(SKU)
    if not item or item.get("sku")!=SKU or item.get("condition")!="NEW":
        raise DraftError("Existing screwdriver inventory not found or not new")
    if offer.get("sku")!=SKU or offer.get("categoryId")!=CATEGORY:
        raise DraftError("Unexpected offer identity/category")
    price=(offer.get("pricingSummary") or {}).get("price") or {}
    if price.get("currency")!="GBP" or str(price.get("value"))!=PRICE:
        raise DraftError("Offer price differs from previously agreed GBP 7.49")
    if offer.get("status")=="PUBLISHED":
        listing_id=str((offer.get("listing") or {}).get("listingId") or "")
        if not listing_id:
            raise DraftError("Live status without listing ID; investigate")
        print("ALREADY LIVE - NO DUPLICATE https://www.ebay.co.uk/itm/"+listing_id,flush=True)
        return
    if offer.get("status")!="UNPUBLISHED" or offer.get("listing"):
        raise DraftError("Unexpected existing offer status; refusing")
    qty=((item.get("availability") or {}).get("shipToLocationAvailability") or {}).get("quantity")
    if qty not in (0,1) or offer.get("availableQuantity") not in (0,1):
        raise DraftError("Unexpected existing inventory quantity")
    previous_title=(item.get("product") or {}).get("title")
    allowed_titles={
        "32 in 1 Precision Screwdriver Set Magnetic Mini Repair Kit Phone Laptop Watch",
        "32 in 1 Precision Screwdriver Set Magnetic Mini Repair Kit Phone Laptop Watch"
    }
    if previous_title not in allowed_titles:
        raise DraftError("Existing item title changed unexpectedly")
    old_urls=(item.get("product") or {}).get("imageUrls") or []
    if old_urls and old_urls!=PHOTO_URLS:
        raise DraftError("Existing kit images differ; refusing overwrite")
    policies=offer.get("listingPolicies") or {}
    if not all(policies.get(x) for x in ("paymentPolicyId","returnPolicyId","fulfillmentPolicyId")):
        raise DraftError("Seller payment/shipping/returns policies missing")
    location=offer.get("merchantLocationKey")
    if not location:
        raise DraftError("Seller dispatch location missing")
    locations=api._request("GET","/location?limit=100").get("locations") or []
    if not any(x.get("merchantLocationKey")==location and x.get("merchantLocationStatus")=="ENABLED" for x in locations):
        raise DraftError("Seller dispatch location not enabled")
    product=dict(item.get("product") or {})
    product.update({
        "title":TITLE,
        "description":DESCRIPTION,
        "imageUrls":PHOTO_URLS,
        "aspects":{
            "Type":["Precision Screwdriver Set"],
            "Number of Pieces":["32"],
            "Features":["Magnetic","Interchangeable Bits"],
            "Colour":["Grey","Black"]
        }
    })
    print("STEP: update screwdriver inventory and image gallery",flush=True)
    ebay_write(api,"PUT","/inventory_item/"+SKU,{
        "product":product,"condition":"NEW",
        "availability":{"shipToLocationAvailability":{"quantity":1}}
    })
    check_item=api.item(SKU)
    if (check_item.get("product",{}).get("imageUrls")!=PHOTO_URLS or
        check_item.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=1):
        raise DraftError("Item photo/stock update not verified")
    update={
        "sku":SKU,"marketplaceId":"EBAY_GB","format":"FIXED_PRICE",
        "categoryId":CATEGORY,"availableQuantity":1,
        "listingDuration":offer.get("listingDuration") or "GTC",
        "listingDescription":DESCRIPTION,
        "pricingSummary":{"price":{"value":PRICE,"currency":"GBP"}},
        "listingPolicies":policies,"merchantLocationKey":location
    }
    print("STEP: update unpublished screwdriver offer",flush=True)
    ebay_write(api,"PUT","/offer/"+offers[0]["offerId"],update)
    checked=api.offer(offers[0]["offerId"])
    if checked.get("status")!="UNPUBLISHED" or checked.get("availableQuantity")!=1:
        raise DraftError("Prepublication offer verification failed")
    print("PREPUBLICATION READY: exactly one unit, seller-owned, GBP 7.49, two images",flush=True)
    print("STEP: publish exact existing screwdriver offer",flush=True)
    published=ebay_write(api,"POST","/offer/"+offers[0]["offerId"]+"/publish")
    listing_id=str(published.get("listingId") or "")
    if not listing_id:
        raise DraftError("Publish response has no listingId; inspect live state before retry")
    final=api.offer(offers[0]["offerId"])
    if (final.get("status")!="PUBLISHED" or
        str((final.get("listing") or {}).get("listingId") or "")!=listing_id):
        raise DraftError("eBay publish response returned ID, but status unverified: "+listing_id)
    print("SUCCESS PUBLISHED £"+PRICE+" QTY 1 https://www.ebay.co.uk/itm/"+listing_id,flush=True)

if __name__=="__main__":
    try:
        if len(sys.argv)!=2:
            raise DraftError("Provide --render-only or --publish")
        if sys.argv[1]=="--render-only":
            render()
        elif sys.argv[1]=="--publish":
            prepare()
        else:
            raise DraftError("Unknown option")
    except (DraftError,OSError,ValueError,TypeError,KeyError) as exc:
        print("SCREWDRIVER PUBLISH STOPPED:",exc,file=sys.stderr)
        sys.exit(1)
