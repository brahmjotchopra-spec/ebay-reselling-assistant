"""Replace main image of the existing live 100-pack air-fryer liner eBay listing.

Uses seller-approved image uploaded as an exact base64 snapshot to this repository.
Never creates or ends a listing. Preserves price, title, description, quantity,
condition, category, fulfilment, returns and payment policies.
"""
import sys,time
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-HOME-AIRFRYER100"
LISTING_ID="880139986215"
PRICE="6.99"
ROOT="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/"
NEW_IMAGE=ROOT+"approved-air-fryer-100-main.jpg"
ORIGINAL_IMAGE=ROOT+"household-air-fryer-liners-100.jpg"

def image_accessible(url):
    for attempt in range(12):
        try:
            request=Request(url,headers={"User-Agent":"Mozilla/5.0"})
            with urlopen(request,timeout=15) as response:
                if (response.status==200 and
                    response.headers.get("Content-Type","").startswith("image/jpeg") and
                    response.read(3)==bytes.fromhex("ffd8ff")):
                    return
        except (HTTPError,URLError,OSError):
            pass
        time.sleep(3)
    raise DraftError("Corrected JPG not publicly available yet in GitHub main branch")

def main():
    image_accessible(NEW_IMAGE)
    api=Inventory(get_token())
    api.check_access()
    offers=api.offers(SKU)
    if len(offers)!=1:
        raise DraftError("Expected exactly one existing air-fryer listing offer")
    offer=api.offer(offers[0]["offerId"])
    if (offer.get("sku")!=SKU or
        offer.get("status")!="PUBLISHED" or
        str((offer.get("listing") or {}).get("listingId"))!=LISTING_ID):
        raise DraftError("Published air-fryer offer or item ID did not match")
    price=(offer.get("pricingSummary") or {}).get("price") or {}
    if price.get("currency")!="GBP" or str(price.get("value"))!=PRICE:
        raise DraftError("Unexpected price; refusing to edit listing")
    item=api.item(SKU)
    if not item or item.get("condition")!="NEW":
        raise DraftError("Expected new-condition inventory item not found")
    product=dict(item.get("product") or {})
    if not (product.get("title") or "").startswith("100 Disposable Brown Paper Air Fryer Liners"):
        raise DraftError("Live item title changed; refusing to overwrite")
    image_urls=product.get("imageUrls") or []
    if image_urls==[NEW_IMAGE]:
        print("ALREADY UPDATED: https://www.ebay.co.uk/itm/"+LISTING_ID)
        return
    if image_urls!=[ORIGINAL_IMAGE]:
        raise DraftError("Other images added by seller; refusing to overwrite")
    available=item.get("availability")
    if not isinstance(available,dict):
        raise DraftError("Missing stock availability field")
    quantity=(available.get("shipToLocationAvailability") or {}).get("quantity")
    if not isinstance(quantity,int) or quantity<0:
        raise DraftError("Cannot preserve stock quantity")
    before_description=product.get("description")
    before_title=product.get("title")
    product["imageUrls"]=[NEW_IMAGE]
    payload={"product":product,"condition":"NEW","availability":available}
    for key in ("conditionDescription","packageWeightAndSize"):
        if key in item: payload[key]=item[key]
    api.create_item(SKU,payload)
    updated=api.item(SKU)
    if (updated.get("product",{}).get("imageUrls")!=[NEW_IMAGE] or
        updated.get("product",{}).get("title")!=before_title or
        updated.get("product",{}).get("description")!=before_description or
        updated.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=quantity):
        raise DraftError("eBay inventory read-back failed")
    final=api.offer(offer["offerId"])
    if (final.get("status")!="PUBLISHED" or
        str((final.get("listing") or {}).get("listingId"))!=LISTING_ID or
        (final.get("pricingSummary") or {}).get("price")!=price or
        final.get("listingPolicies")!=offer.get("listingPolicies") or
        final.get("merchantLocationKey")!=offer.get("merchantLocationKey")):
        raise DraftError("Live eBay offer, price, listing or policies changed")
    print("SUCCESS: UPDATED LIVE AIR FRYER LINER EBAY MAIN PHOTO")
    print("ITEM URL https://www.ebay.co.uk/itm/"+LISTING_ID)
    print("MAIN IMAGE "+NEW_IMAGE)
    print("PRICE GBP",PRICE,"QUANTITY",quantity)

if __name__=="__main__":
    try:
        main()
    except (DraftError,ValueError,KeyError,TypeError,OSError) as exc:
        print("AIR FRYER IMAGE UPDATE FAILED:",exc,file=sys.stderr)
        sys.exit(1)
