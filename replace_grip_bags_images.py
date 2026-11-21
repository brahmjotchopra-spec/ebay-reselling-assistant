"""Replace grip-seal bag illustrations with exact Amazon product-page images where available.

Preserves live listing, price, category, stock, condition, policies, and origin.
Does not create new listings. Note: use retailer images only with rights-holder permission.
"""
import sys
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-BULK-GRIP-MIX-100"
LISTING_ID="880139960160"
PRICE="4.99"
ORIGINAL="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/bulk-grip-seal-bags.jpg"
BASE="https://m.media-amazon.com/images/I/"
# The selected IDs are from the same mawmuaw 500-pack Amazon UK listing the user supplied.
# Omit the five-sizes infographic displaying 100 of each size if it is later shown:
# the actual eBay lot contains only 20 per size.
PHOTO_IDS=["71+4O0VhFtL","41LQQmu8bzL","413AdD2gIgL","512fpIxdLbL","41Hb119mA4L"]
PHOTOS=[BASE+code+"._AC_SL1500_.jpg" for code in PHOTO_IDS]

def check_images():
    try:
        from PIL import Image
    except ImportError as exc:
        raise DraftError("Pillow missing in workflow") from exc
    for index,url in enumerate(PHOTOS,1):
        try:
            request=Request(url,method="GET",headers={"User-Agent":"Mozilla/5.0"})
            with urlopen(request,timeout=20) as response:
                data=response.read(10000000)
                if response.status!=200 or not response.headers.get("Content-Type","").startswith("image/"):
                    raise DraftError("Source image "+str(index)+" is unavailable")
            im=Image.open(BytesIO(data))
            if min(im.size)<500:
                raise DraftError("Source image "+str(index)+" too small: "+str(im.size))
            print("Image "+str(index)+" checked, dimensions "+str(im.size))
        except (URLError,HTTPError,OSError) as exc:
            raise DraftError("Cannot download source image "+str(index)+" ("+type(exc).__name__+")") from None

def main():
    check_images()
    api=Inventory(get_token())
    api.check_access()
    offers=api.offers(SKU)
    if len(offers)!=1:raise DraftError("Unexpected number of offers for grip bags")
    offer=api.offer(offers[0]["offerId"])
    if offer.get("status")!="PUBLISHED" or str((offer.get("listing") or {}).get("listingId"))!=LISTING_ID:
        raise DraftError("Expected live grip-bag listing not found")
    price=(offer.get("pricingSummary") or {}).get("price") or {}
    if price.get("value")!=PRICE or price.get("currency")!="GBP":raise DraftError("Price mismatch")
    item=api.item(SKU)
    if not item or item.get("condition")!="NEW":raise DraftError("Inventory item missing or unexpected condition")
    product=dict(item.get("product") or {})
    if not product.get("title","").startswith("100 Small Clear Resealable Grip Seal Bags"):
        raise DraftError("Product mismatch")
    current=product.get("imageUrls") or []
    if current==PHOTOS:
        print("IMAGES ALREADY UPDATED", "https://www.ebay.co.uk/itm/"+LISTING_ID)
        return
    if current!=[ORIGINAL]:
        raise DraftError("Photo changed elsewhere; refusing overwrite")
    avail=item.get("availability")
    if not isinstance(avail,dict) or not isinstance((avail.get("shipToLocationAvailability") or {}).get("quantity"),int):
        raise DraftError("Cannot preserve stock count")
    stock=avail["shipToLocationAvailability"]["quantity"]
    product["imageUrls"]=PHOTOS
    # Explicit disclosure that other objects in marketing pictures are demonstrative.
    desc=product.get("description") or ""
    note="Photos show examples of what bags can hold. Only 100 empty bags are supplied (20 of each of five sizes); contents shown are not included."
    if note not in desc:
        product["description"]=desc+" "+note
    api.create_item(SKU,{"product":product,"condition":"NEW","availability":avail})
    verified=api.item(SKU)
    if (verified.get("product",{}).get("imageUrls")!=PHOTOS
        or verified.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=stock):
        raise DraftError("Photo change was not confirmed or stock changed")
    after=api.offer(offer["offerId"])
    if (after.get("status")!="PUBLISHED" or
        str((after.get("listing") or {}).get("listingId"))!=LISTING_ID or
        (after.get("pricingSummary") or {}).get("price")!=price):
        raise DraftError("Live listing, price or offer status changed unexpectedly")
    print("UPDATED LIVE BAG LISTING PHOTOS:",len(PHOTOS))
    print("LIVE https://www.ebay.co.uk/itm/"+LISTING_ID)
    print("PRICE GBP "+PRICE+" QUANTITY",stock)

if __name__=="__main__":
    try:main()
    except (DraftError, ValueError, OSError, KeyError, TypeError) as exc:
        print("IMAGE UPDATE STOPPED:",exc,file=sys.stderr)
        sys.exit(1)
