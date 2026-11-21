"""Update a single live eBay listing with eBay Picture Services (EPS) photos.

Fetches four exact-source product images matching seller-provided screenshots,
excluding supplier's 500-pack size guide to avoid misleading 100-pack buyers.
Uses the supported Media API createImageFromFile, and changes only item images,
an explicit empty-contents disclosure, and nothing else.
"""
import sys
import json
import uuid
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from PIL import Image
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-BULK-GRIP-MIX-100"
LISTING_ID="880139960160"
PRICE="4.99"
ORIGINAL="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/bulk-grip-seal-bags.jpg"
AMAZON="https://m.media-amazon.com/images/I/"
IDS=["71+4O0VhFtL","413AdD2gIgL","41Hb119mA4L","51GF8OUL04L"]
MEDIA_URL="https://apim.ebay.com/commerce/media/v1_beta/image/create_image_from_file"

def safe_error(exc):
    try:
        decoded=json.loads(exc.read())
        return "HTTP "+str(exc.code)+" codes "+str([e.get("errorId") for e in decoded.get("errors",[])])
    except Exception:
        return "HTTP "+str(exc.code)+" (unreadable response)"

def get_image(identifier):
    url=AMAZON+identifier+"._AC_SL1500_.jpg"
    try:
        request=Request(url,headers={"User-Agent":"Mozilla/5.0"})
        with urlopen(request,timeout=20) as response:
            if response.status!=200 or not response.headers.get("Content-Type","").startswith("image/"):
                raise DraftError("Unavailable supplier image")
            data=response.read(10000000)
    except (HTTPError,URLError,OSError):
        raise DraftError("Cannot retrieve one selected photo") from None
    try:
        with Image.open(BytesIO(data)) as inp:
            im=inp.convert("RGB")
    except Exception:
        raise DraftError("Selected photo is not a readable image") from None
    if max(im.size)<400:
        raise DraftError("Source photo resolution too low")
    # Improve eBay display while preserving the source photograph and its aspect.
    if max(im.size)<1050:
        scale=1050/max(im.size)
        newsize=(round(im.width*scale),round(im.height*scale))
        im=im.resize(newsize,Image.Resampling.LANCZOS)
    output=BytesIO()
    im.save(output,format="JPEG",quality=88,optimize=True)
    print("Photo inspected:",im.size,"JPEG bytes:",len(output.getvalue()))
    return output.getvalue()

def upload_to_ebay(token,payload,filename):
    boundary="----EBAY_IMAGE_"+uuid.uuid4().hex
    header=(
        "--"+boundary+"\r\n"
        'Content-Disposition: form-data; name="image"; filename="'+filename+'"\r\n'
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode("ascii")
    body=header+payload+("\r\n--"+boundary+"--\r\n").encode("ascii")
    request=Request(MEDIA_URL,data=body,method="POST",headers={
        "Authorization":"Bearer "+token,
        "Content-Type":"multipart/form-data; boundary="+boundary,
        "Accept":"application/json",
    })
    try:
        with urlopen(request,timeout=35) as response:
            raw=response.read()
            data=json.loads(raw) if raw.strip() else {}
            if response.status!=201:
                raise DraftError("Media API did not accept photo")
            pic=data.get("imageUrl") or data.get("imageURL")
            if not pic:
                # A getImage request can recover the EPS URL by image ID if necessary.
                location=response.headers.get("Location") or ""
                if not location.startswith("https://"):
                    raise DraftError("Media API succeeded but no image URL was returned")
                pic_req=Request(location.replace("https://apim.ebay.com","https://api.ebay.com"),
                                headers={"Authorization":"Bearer "+token,"Accept":"application/json"})
                with urlopen(pic_req,timeout=20) as pic_res:
                    pic=json.loads(pic_res.read()).get("imageUrl")
            if not isinstance(pic,str) or not pic.startswith("https://"):
                raise DraftError("Invalid EPS photo URL")
            return pic
    except HTTPError as exc:
        raise DraftError("Media upload rejected: "+safe_error(exc)) from None
    except (URLError,OSError) as exc:
        raise DraftError("Media upload unavailable ("+type(exc).__name__+")") from None

def main():
    api=Inventory(get_token())
    api.check_access()
    offers=api.offers(SKU)
    if len(offers)!=1:
        raise DraftError("Expected one existing grip-bag eBay offer")
    offer=api.offer(offers[0]["offerId"])
    if (offer.get("status")!="PUBLISHED" or
        str((offer.get("listing") or {}).get("listingId"))!=LISTING_ID):
        raise DraftError("Unexpected live offer identity")
    price=(offer.get("pricingSummary") or {}).get("price") or {}
    if price.get("value")!=PRICE or price.get("currency")!="GBP":
        raise DraftError("Price mismatch; refusing edit")
    item=api.item(SKU)
    if not item or item.get("condition")!="NEW":
        raise DraftError("Listing item missing/condition mismatch")
    product=dict(item.get("product") or {})
    if not product.get("title","").startswith("100 Small Clear Resealable Grip Seal Bags"):
        raise DraftError("Unexpected item title")
    old=product.get("imageUrls") or []
    if old!=[ORIGINAL]:
        if len(old)==len(IDS) and all("ebayimg.com" in x for x in old):
            print("ALREADY UPDATED WITH EPS PHOTOS",LISTING_ID)
            return
        raise DraftError("Images changed elsewhere; don't overwrite")
    avail=item.get("availability") or {}
    qty=(avail.get("shipToLocationAvailability") or {}).get("quantity")
    if not isinstance(qty,int) or qty<0:
        raise DraftError("Cannot preserve item stock quantity")
    # Download/validate all images before changing the listing.
    source_images=[get_image(photo_id) for photo_id in IDS]
    token=get_token()
    eps=[upload_to_ebay(token,blob,f"grip_bags_{i}.jpg") for i,blob in enumerate(source_images,1)]
    if len(eps)!=len(IDS) or len(set(eps))!=len(IDS):
        raise DraftError("EPS images incomplete or duplicated")
    product["imageUrls"]=eps
    note=" Pictures show example uses only. You receive 100 EMPTY bags, 20 of each of five listed sizes. Items shown inside bags are NOT included."
    if note not in (product.get("description") or ""):
        product["description"]=(product.get("description") or "")+note
    payload={"product":product,"condition":"NEW","availability":avail}
    for field in ("conditionDescription","packageWeightAndSize"):
        if field in item:payload[field]=item[field]
    api.create_item(SKU,payload)
    checked=api.item(SKU)
    if (checked.get("product",{}).get("imageUrls")!=eps or
        checked.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=qty):
        raise DraftError("Item photos/quantity not verified after update")
    after=api.offer(offer["offerId"])
    if (after.get("status")!="PUBLISHED" or
        str((after.get("listing") or {}).get("listingId"))!=LISTING_ID or
        (after.get("pricingSummary") or {}).get("price")!=price):
        raise DraftError("Listing state, ID or price changed")
    print("SUCCESS: UPDATED FOUR PHOTOS ON LIVE GRIP-BAG LISTING")
    print("LISTING URL https://www.ebay.co.uk/itm/"+LISTING_ID)
    print("PRICE GBP",PRICE,"STOCK QUANTITY",qty)
    print("EPS images uploaded: ",len(eps))

if __name__=="__main__":
    try:main()
    except (DraftError,ValueError,OSError,KeyError,TypeError) as exc:
        print("IMAGE UPDATE STOPPED:",exc,file=sys.stderr)
        sys.exit(1)
