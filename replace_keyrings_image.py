"""Replace the photo on a specific live eBay UK keyrings listing.

Updates only the product image of a single Inventory API item.
Preserves stock and every existing product attribute. Never publishes,
ends, duplicates, changes price, or changes shipping policies.
"""
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-AMZ-RINGS-25MM-50"
LISTING_ID="880139841751"
TITLE="50 x 25mm Silver Split Key Rings Metal Keyring Hoops Keychain Craft Rings"
OLD_URL="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/keyrings-50.jpg"
NEW_URL="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/keyrings-50-realistic.jpg"

def photo_reachable():
    for n in range(12):
        try:
            request=Request(NEW_URL,method="GET",headers={"User-Agent":"Mozilla/5.0"})
            with urlopen(request,timeout=12) as response:
                head=response.read(3)
                if response.status==200 and response.headers.get("Content-Type","").startswith("image/") and head==b"\\xff\\xd8\\xff":
                    return True
        except (URLError,HTTPError,OSError):
            pass
        time.sleep(3)
    return False

def main():
    if not photo_reachable():
        raise DraftError("New photographic-style image not yet available on GitHub")
    api=Inventory(get_token())
    api.check_access()
    offer_list=api.offers(SKU)
    if len(offer_list)!=1:raise DraftError("Expected exactly one keyrings offer")
    offer=api.offer(offer_list[0]["offerId"])
    if (offer.get("sku")!=SKU or offer.get("status")!="PUBLISHED" or
        str(offer.get("listing",{}).get("listingId"))!=LISTING_ID):
        raise DraftError("Refusing edit: the existing published listing ID/state doesn't match")
    if offer.get("pricingSummary",{}).get("price",{}).get("value")!="5.79":
        raise DraftError("Price not as expected; refusing to alter anything")
    current=api.item(SKU)
    if current is None or current.get("sku")!=SKU:
        raise DraftError("Expected live inventory item missing")
    product=dict(current.get("product") or {})
    if product.get("title")!=TITLE:raise DraftError("Existing item title doesn't match")
    original=product.get("imageUrls") or []
    if original==[NEW_URL]:
        print("IMAGE ALREADY UPDATED for live listing "+LISTING_ID)
        return
    if len(original)!=1 or original[0]!=OLD_URL:
        raise DraftError("Current image URL differs from expected previous listing picture")
    avail=current.get("availability")
    if not isinstance(avail,dict) or "shipToLocationAvailability" not in avail:
        raise DraftError("Cannot safely preserve current inventory availability")
    qty=avail["shipToLocationAvailability"].get("quantity")
    if type(qty) is not int or qty<0:
        raise DraftError("Unexpected inventory quantity")
    product["imageUrls"]=[NEW_URL]
    payload={
        "product":product,
        "condition":current.get("condition","NEW"),
        "availability":avail,
    }
    for key in ("conditionDescription","packageWeightAndSize"):
        if key in current: payload[key]=current[key]
    api.create_item(SKU,payload)
    verified=api.item(SKU)
    if verified.get("product",{}).get("imageUrls")!=[NEW_URL]:
        raise DraftError("Photo revision not reflected in eBay inventory")
    if verified.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=qty:
        raise DraftError("Inventory quantity changed unexpectedly")
    updated_offer=api.offer(offer["offerId"])
    if (updated_offer.get("status")!="PUBLISHED" or
        str(updated_offer.get("listing",{}).get("listingId"))!=LISTING_ID):
        raise DraftError("Unexpected active offer status after image revision")
    print("IMAGE REPLACED ON LIVE EBAY LISTING "+LISTING_ID)
    print("New photo URL:",NEW_URL)
    print("Price unchanged: GBP 5.79; quantity preserved:",qty)
    print("Live listing: https://www.ebay.co.uk/itm/"+LISTING_ID)

if __name__=="__main__":
    try: main()
    except (DraftError, ValueError, TypeError, OSError) as exc:
        print("REPLACE IMAGE FAILED:",exc,file=sys.stderr)
        sys.exit(1)
