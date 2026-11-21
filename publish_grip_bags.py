"""Publish one physically stocked 100-bag mixed-size lot via the existing eBay offer.

Idempotent and limited to one ready-to-pack lot (20 of each of 5 sizes).
Does not edit other listings or create duplicate offers.
"""
import sys, time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-BULK-GRIP-MIX-100"
PHOTO="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/bulk-grip-seal-bags.jpg"
TITLE="100 Small Clear Resealable Grip Seal Bags 5 Sizes Mini Ziplock Jewellery Crafts"
DESC=(
    "100 clear mini resealable grip-seal bags, selected from the 500-piece 5-size stock set. "
    "This pack contains 20 bags each of five sizes: 2.5 x 3.5 cm, 3 x 3 cm, 3 x 4 cm, "
    "3.5 x 5 cm and 4 x 6 cm. These are very small bags; please check dimensions carefully "
    "before ordering. Transparent PE plastic with press-to-close seal. Useful for beads, "
    "jewellery findings, screws, small craft parts and other tiny items. "
    "Only empty bags included; no jewellery or accessories. "
    "Product image is an original digital illustration of resealable bags, not a photograph "
    "of the physical stock. You will receive the exact size assortment stated above."
)
PRICE="4.99"
CATEGORY="86174"
QUANTITY=1

def check_photo():
    for _ in range(6):
        try:
            req=Request(PHOTO,method="GET",headers={"User-Agent":"Mozilla/5.0"})
            with urlopen(req,timeout=12) as resp:
                if resp.status==200 and resp.headers.get("Content-Type","").startswith("image/") and resp.read(3)==bytes.fromhex("ffd8ff"):
                    return
        except (URLError, HTTPError, OSError):
            pass
        time.sleep(2)
    raise DraftError("Product image not available to eBay")

def main():
    check_photo()
    api=Inventory(get_token())
    api.check_access()
    offers=api.offers(SKU)
    if len(offers)!=1: raise DraftError("Expected exactly one existing grip-bag offer")
    offer=api.offer(offers[0]["offerId"])
    if offer.get("sku")!=SKU: raise DraftError("SKU mismatch")
    if offer.get("status")=="PUBLISHED":
        listing_id=(offer.get("listing") or {}).get("listingId")
        if not listing_id: raise DraftError("Published but listing ID missing")
        print("ALREADY LIVE (no duplicate): https://www.ebay.co.uk/itm/"+str(listing_id))
        return
    if offer.get("status")!="UNPUBLISHED" or offer.get("listing"):
        raise DraftError("Unexpected offer state")
    price=(offer.get("pricingSummary") or {}).get("price") or {}
    if offer.get("categoryId")!=CATEGORY or str(price.get("value"))!=PRICE or price.get("currency")!="GBP":
        raise DraftError("Category or original offer price changed")
    inventory=api.item(SKU)
    if not inventory or inventory.get("sku")!=SKU or inventory.get("condition")!="NEW":
        raise DraftError("Stock item or condition mismatch")
    if inventory.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity") not in (0,1):
        raise DraftError("Unexpected inventory stock quantity")
    if offer.get("availableQuantity") not in (0,1): raise DraftError("Unexpected offer quantity")
    policies=offer.get("listingPolicies") or {}
    if not all(policies.get(k) for k in ("fulfillmentPolicyId","returnPolicyId","paymentPolicyId")):
        raise DraftError("Shipping/payment/return policies missing")
    if not offer.get("merchantLocationKey"): raise DraftError("Dispatch origin missing")
    previous_title=(inventory.get("product") or {}).get("title") or ""
    if not previous_title.startswith("100 Clear Small Resealable Grip Seal Bags"):
        raise DraftError("Existing inventory not expected candidate")
    product=dict(inventory.get("product") or {})
    product["title"]=TITLE
    product["description"]=DESC
    product["imageUrls"]=[PHOTO]
    aspects=dict(product.get("aspects") or {})
    aspects["Type"]=["Reclosable Bags"]
    aspects["Colour"]=["Clear"]
    aspects["Material"]=["Plastic"]
    aspects["Features"]=["Resealable"]
    product["aspects"]=aspects
    api.create_item(SKU,{"product":product,"condition":"NEW","availability":{"shipToLocationAvailability":{"quantity":QUANTITY}}})
    check=api.item(SKU)
    if check.get("product",{}).get("imageUrls")!=[PHOTO] or check.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=QUANTITY:
        raise DraftError("Image or stock not saved")
    payload={
      "sku":SKU,"marketplaceId":"EBAY_GB","format":"FIXED_PRICE",
      "categoryId":CATEGORY,"availableQuantity":QUANTITY,
      "listingDuration":offer.get("listingDuration") or "GTC",
      "listingDescription":DESC,"pricingSummary":{"price":{"value":PRICE,"currency":"GBP"}},
      "listingPolicies":policies,"merchantLocationKey":offer["merchantLocationKey"]
    }
    api._request("PUT","/offer/"+offer["offerId"],payload)
    check_offer=api.offer(offer["offerId"])
    if check_offer.get("status")!="UNPUBLISHED" or check_offer.get("availableQuantity")!=QUANTITY:
        raise DraftError("Offer failed readiness check")
    result=api._request("POST","/offer/"+offer["offerId"]+"/publish")
    listing_id=result.get("listingId")
    if not listing_id:raise DraftError("eBay did not return a listing ID; reconcile before retry")
    confirmed=api.offer(offer["offerId"])
    if confirmed.get("status")!="PUBLISHED" or str((confirmed.get("listing") or {}).get("listingId"))!=str(listing_id):
        raise DraftError("eBay publication could not be independently verified")
    print("PUBLISHED 100 SMALL RESEALABLE BAGS ON EBAY UK")
    print("LISTING URL: https://www.ebay.co.uk/itm/"+str(listing_id))
    print("Price GBP "+PRICE+" quantity "+str(QUANTITY))
    print("Seller must pack 20 bags of each listed size for each order")

if __name__=="__main__":
    try:main()
    except (DraftError, ValueError, OSError, KeyError, TypeError) as exc:
        print("GRIP BAG PUBLISH ERROR:",exc,file=sys.stderr)
        sys.exit(1)
