"""Replace old vector illustration with the newly generated high-quality main image.

Updates only the live 6mm jump-ring listing's main image. Never changes
listing ID, available quantity, price, delivery or returns. Idempotent.
"""
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-BULK-JUMP-6MM-100"
LISTING_ID="880139932248"
OLD_URL="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/bulk-6mm-jump-rings.jpg"
NEW_URL="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/6mm-jump-rings-ai-photo-main.jpg"

def photo_reachable():
    for attempt in range(9):
        try:
            req=Request(NEW_URL,method="GET",headers={"User-Agent":"Mozilla/5.0"})
            with urlopen(req,timeout=18) as r:
                magic=r.read(3)
                if r.status==200 and magic==bytes.fromhex("ffd8ff") and "image/jpeg" in r.headers.get("Content-Type",""):
                    return
        except (URLError,HTTPError,OSError):
            pass
        time.sleep(3)
    raise DraftError("Replacement picture not yet publicly accessible as a JPEG")

def main():
    photo_reachable()
    api=Inventory(get_token())
    api.check_access()
    offers=api.offers(SKU)
    if len(offers)!=1:
        raise DraftError("Expected exactly one offer for 6mm jump rings")
    offer=api.offer(offers[0]["offerId"])
    if (offer.get("sku")!=SKU or offer.get("status")!="PUBLISHED" or
        str((offer.get("listing") or {}).get("listingId"))!=LISTING_ID):
        raise DraftError("Cannot verify live listing ID and status")
    price=(offer.get("pricingSummary") or {}).get("price") or {}
    if price.get("value")!="3.99" or price.get("currency")!="GBP":
        raise DraftError("Live price has changed unexpectedly")
    item=api.item(SKU)
    if not item or item.get("sku")!=SKU:
        raise DraftError("Live eBay inventory item missing")
    product=dict(item.get("product") or {})
    if not product.get("title","").startswith("100 x 6mm Silver Tone Open Jump Rings"):
        raise DraftError("Live product title does not match")
    old_images=product.get("imageUrls") or []
    if old_images==[NEW_URL]:
        print("NEW MAIN IMAGE ALREADY PRESENT — no duplicate or edit needed")
        print("LIVE URL https://www.ebay.co.uk/itm/"+LISTING_ID)
        return
    if old_images!=[OLD_URL]:
        raise DraftError("Unexpected existing images; refusing to overwrite them")
    avail=item.get("availability")
    if not isinstance(avail,dict) or "shipToLocationAvailability" not in avail:
        raise DraftError("Missing stock availability structure")
    qty=avail["shipToLocationAvailability"].get("quantity")
    if not isinstance(qty,int) or qty<0:
        raise DraftError("Current physical inventory quantity invalid")
    condition=item.get("condition")
    if condition!="NEW":
        raise DraftError("Condition mismatch")
    product["imageUrls"]=[NEW_URL]
    updated={"product":product,"condition":condition,"availability":avail}
    for field in ("conditionDescription","packageWeightAndSize"):
        if field in item:
            updated[field]=item[field]
    api.create_item(SKU,updated)
    verified=api.item(SKU)
    if ((verified.get("product") or {}).get("imageUrls")!=[NEW_URL] or
        verified.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=qty):
        raise DraftError("eBay inventory image or quantity read-back failed")
    current=api.offer(offer["offerId"])
    if (current.get("status")!="PUBLISHED" or
        str((current.get("listing") or {}).get("listingId"))!=LISTING_ID or
        (current.get("pricingSummary") or {}).get("price")!=price):
        raise DraftError("Live status, listing ID or price changed unexpectedly")
    print("SUCCESS: REPLACED IMAGE ON LIVE EBAY LISTING "+LISTING_ID)
    print("LIVE URL https://www.ebay.co.uk/itm/"+LISTING_ID)
    print("Price preserved: GBP 3.99; quantity preserved:",qty)
    print("New main image:",NEW_URL)

if __name__=="__main__":
    try:
        main()
    except (DraftError,OSError,ValueError,TypeError,KeyError) as exc:
        print("IMAGE REPLACEMENT STOPPED:",exc,file=sys.stderr)
        sys.exit(1)
