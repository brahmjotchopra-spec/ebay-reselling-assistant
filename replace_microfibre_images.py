"""Replace the main and secondary photos on the existing live microfibre eBay listing.

Images are original AI-created representations provided and approved by the seller.
Never creates another listing or changes price, stock, category, postage or return policies.
"""
import sys,time
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from ebay_client import Inventory,DraftError,get_token

SKU="DRAFT-HOME-MICROFIBRE20"
LISTING_ID="880139985405"
PRICE="8.99"
OLD="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/household-microfibre-20.jpg"
ROOT="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/"
FILES=["microfibre_main_new_ebay.jpg",
       "microfibre_details_new_ebay.jpg",
       "microfibre_cleaning_new_ebay.jpg",
       "microfibre_glass_new_ebay.jpg"]
NEW=[ROOT+x for x in FILES]

def verify_image_url(url):
    for attempt in range(10):
        try:
            req=Request(url,method="GET",headers={"User-Agent":"Mozilla/5.0"})
            with urlopen(req,timeout=20) as r:
                if r.status==200 and r.read(3)==bytes.fromhex("ffd8ff") and
                   "image/jpeg" in r.headers.get("Content-Type",""):
                    return
        except (HTTPError,URLError,OSError):
            pass
        time.sleep(3)
    raise DraftError("New photo not publicly accessible after retries: "+url.rsplit("/",1)[-1])

def main():
    for url in NEW:verify_image_url(url)
    api=Inventory(get_token())
    api.check_access()
    offers=api.offers(SKU)
    if len(offers)!=1:raise DraftError("Expected exactly one 20-pack microfibre offer")
    offer=api.offer(offers[0]["offerId"])
    if (offer.get("status")!="PUBLISHED" or offer.get("sku")!=SKU or
        str((offer.get("listing") or {}).get("listingId"))!=LISTING_ID):
        raise DraftError("Live listing mismatch; refusing change")
    price=(offer.get("pricingSummary") or {}).get("price") or {}
    if price.get("value")!=PRICE or price.get("currency")!="GBP":
        raise DraftError("Live listing price does not match approved £8.99")
    item=api.item(SKU)
    if not item or item.get("condition")!="NEW":
        raise DraftError("Unexpected inventory or condition")
    product=dict(item.get("product") or {})
    if not product.get("title","").startswith("20 Pack Microfibre Cleaning Cloths"):
        raise DraftError("Wrong product; refusing image replacement")
    existing=product.get("imageUrls") or []
    if existing==NEW:
        print("ALREADY UPDATED: https://www.ebay.co.uk/itm/"+LISTING_ID)
        return
    if existing!=[OLD]:
        raise DraftError("The old images have changed; refusing to overwrite unfamiliar images")
    availability=item.get("availability")
    if not isinstance(availability,dict):
        raise DraftError("Inventory availability structure missing")
    stock=(availability.get("shipToLocationAvailability") or {}).get("quantity")
    if not isinstance(stock,int) or stock<0:
        raise DraftError("Cannot preserve stock quantity")
    original_title=product["title"]
    original_description=product.get("description")
    product["imageUrls"]=NEW
    payload={"product":product,"condition":"NEW","availability":availability}
    for key in ("conditionDescription","packageWeightAndSize"):
        if key in item:payload[key]=item[key]
    api.create_item(SKU,payload)
    item_after=api.item(SKU)
    photos=(item_after.get("product") or {}).get("imageUrls")
    if photos!=NEW:
        raise DraftError("Photo update not confirmed by eBay inventory")
    if (item_after.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=stock
        or item_after.get("product",{}).get("title")!=original_title
        or item_after.get("product",{}).get("description")!=original_description):
        raise DraftError("Inventory quantity, title or description unexpectedly changed")
    offer_after=api.offer(offer["offerId"])
    if (offer_after.get("status")!="PUBLISHED" or
        str((offer_after.get("listing") or {}).get("listingId"))!=LISTING_ID or
        (offer_after.get("pricingSummary") or {}).get("price")!=price):
        raise DraftError("Live offer/price/listing ID changed unexpectedly")
    print("SUCCESS: REPLACED FOUR LIVE EBAY PHOTOS")
    print("LISTING https://www.ebay.co.uk/itm/"+LISTING_ID)
    print("PRICE GBP "+PRICE+"; QUANTITY "+str(stock)+"; UPDATED IMAGES "+str(len(NEW)))
    for url in photos:print("IMAGE",url)

if __name__=="__main__":
    try:main()
    except (DraftError,ValueError,OSError,KeyError,TypeError) as exc:
        print("MICROFIBRE IMAGE UPDATE FAILED:",exc,file=sys.stderr)
        sys.exit(1)
