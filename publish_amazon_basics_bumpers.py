"""Publish one Amazon Basics 300-piece bumper pack on eBay UK after user reports
having one pack on 22 Nov 2026. Does not purchase any stock or duplicate an offer.
Images are original digital illustrations, explicitly disclosed in description.
"""
import sys,time
from urllib.request import Request,urlopen
from ebay_client import Inventory,get_token,DraftError

SKU="DRAFT-AMZ-BASICS-BUMPER300-1"
CATEGORY="259153"
PRICE="10.99"
QTY=1
TITLE="Amazon Basics 300 Clear Self Adhesive Rubber Bumper Pads Cabinet Door Stops"
BASE="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/"
PHOTOS=[BASE+"amazon-basics-bumpers-300-main.jpg",BASE+"amazon-basics-bumpers-300-details.jpg"]
REF_SKU="DRAFT-HOME-MICROFIBRE20"
SOURCE_URL="https://www.amazon.co.uk/dp/B087MG3G76"
DESCRIPTION=(
    "ONE Amazon Basics set of 300 clear self-adhesive rubber bumper pads in an "
    "assortment of shapes and sizes, for cabinet doors, drawers, cupboards and "
    "furniture. Helps cushion closing contact, protect surfaces and reduce "
    "noise. Suitable for clean, dry surfaces where self-adhesive pads can be used. "
    "Pack composition (pieces): 100 small round, 50 medium round, 20 large square, "
    "20 small square, 50 flat round, 35 raised domes, 25 round pads. "
    "Total 300 bumper pads. Exact dimensions depend on each pad design. "
    "One 300-piece pack is included; no furniture or other accessories. "
    "Please note: the listing gallery uses ORIGINAL DIGITAL ILLUSTRATIONS showing "
    "this type of assortment, NOT photographs of the exact physical stock. "
    "The layout, appearance and individual pads may differ; supplied item is "
    "the genuine Amazon Basics 300-piece assorted bumper pad product."
)
POLICY_KEYS=("paymentPolicyId","returnPolicyId","fulfillmentPolicyId")

def images_ok():
    for url in PHOTOS:
        for attempt in range(16):
            try:
                req=Request(url,headers={"User-Agent":"Mozilla/5.0"})
                with urlopen(req,timeout=15) as f:
                    if (f.status==200 and "image/jpeg" in f.headers.get("Content-Type","")
                        and f.read(3)==b"\xff\xd8\xff"):
                        break
            except Exception:
                pass
            time.sleep(4)
        else:
            raise DraftError("Listing illustration not publicly readable: "+url)

def main():
    images_ok()
    api=Inventory(get_token())
    api.check_access()
    existing_offers=api.offers(SKU)
    if len(existing_offers)>1:
        raise DraftError("Duplicate SKU offers found. Manual review required")
    if existing_offers:
        cur=api.offer(existing_offers[0]["offerId"])
        if cur.get("status")=="PUBLISHED":
            lid=(cur.get("listing") or {}).get("listingId")
            if not lid: raise DraftError("Already published but listing ID not returned")
            print("ALREADY LIVE: https://www.ebay.co.uk/itm/"+str(lid),flush=True)
            return
        if cur.get("status")!="UNPUBLISHED" or cur.get("sku")!=SKU or cur.get("listing"):
            raise DraftError("Existing offer has unexpected state; no changes")
        if cur.get("categoryId")!=CATEGORY:
            raise DraftError("Existing offer category differs; no changes")
        oldprice=(cur.get("pricingSummary") or {}).get("price") or {}
        if oldprice.get("currency")!="GBP" or str(oldprice.get("value"))!=PRICE:
            raise DraftError("Existing offer price differs; no changes")

    previous=api.item(SKU)
    if previous is not None:
        ptitle=(previous.get("product") or {}).get("title","")
        if not ptitle.startswith("Amazon Basics 300 Clear Self Adhesive Rubber Bumper Pads"):
            raise DraftError("Existing inventory has unexpected title")
        stock=(previous.get("availability") or {}).get("shipToLocationAvailability") or {}
        if stock.get("quantity") not in (0,1):
            raise DraftError("Existing stock quantity unexpected")

    ref=api.offers(REF_SKU)
    if len(ref)!=1: raise DraftError("Known live household reference offer not found")
    published_ref=api.offer(ref[0]["offerId"])
    if published_ref.get("status")!="PUBLISHED":
        raise DraftError("Reference seller offer is not live")
    policies=published_ref.get("listingPolicies") or {}
    location=published_ref.get("merchantLocationKey")
    if not location or not all(policies.get(k) for k in POLICY_KEYS):
        raise DraftError("Missing existing business policies / dispatch location")
    policies={k:policies[k] for k in POLICY_KEYS}
    locs=api._request("GET","/location?limit=100").get("locations") or []
    if not any(x.get("merchantLocationKey")==location and
               x.get("merchantLocationStatus")=="ENABLED" for x in locs):
        raise DraftError("Dispatch location is disabled")
    inventory={
        "product":{
            "title":TITLE,"description":DESCRIPTION,
            "imageUrls":PHOTOS,
            "aspects":{
                "Brand":["Amazon Basics"],
                "Type":["Cabinet Door Bumper"],
                "Material":["Rubber"],
                "Colour":["Clear"],
                "Features":["Self-Adhesive"],
                "Number in Pack":["300"]
            }
        },
        "condition":"NEW",
        "availability":{"shipToLocationAvailability":{"quantity":QTY}}
    }
    offer={
        "sku":SKU,
        "marketplaceId":"EBAY_GB",
        "format":"FIXED_PRICE",
        "availableQuantity":QTY,
        "categoryId":CATEGORY,
        "listingDuration":"GTC",
        "listingDescription":DESCRIPTION,
        "pricingSummary":{"price":{"value":PRICE,"currency":"GBP"}},
        "listingPolicies":policies,
        "merchantLocationKey":location
    }
    api.create_item(SKU,inventory)
    check=api.item(SKU)
    if (check.get("product",{}).get("imageUrls")!=PHOTOS or
        check.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=QTY):
        raise DraftError("eBay inventory image/quantity did not verify")
    if existing_offers:
        offer_id=existing_offers[0]["offerId"]
        api._request("PUT","/offer/"+offer_id,offer)
        print("Reused previously unpublished offer; no duplicate",flush=True)
    else:
        offer_id=api.create_offer(offer)
        print("Created fresh eBay inventory offer",flush=True)
    current=api.offer(offer_id)
    if (current.get("status")!="UNPUBLISHED" or current.get("listing") or
        current.get("availableQuantity")!=QTY or
        current.get("categoryId")!=CATEGORY or
        str((current.get("pricingSummary") or {}).get("price",{}).get("value"))!=PRICE):
        raise DraftError("Prepublish offer state failed verification")
    result=api._request("POST","/offer/"+offer_id+"/publish")
    lid=result.get("listingId")
    if not lid:
        raise DraftError("Publish response missing listing ID; inspect live state before retry")
    verified=api.offer(offer_id)
    if (verified.get("status")!="PUBLISHED" or
        str((verified.get("listing") or {}).get("listingId"))!=str(lid)):
        raise DraftError("Publish response not verifiable; inspect live state")
    print("SUCCESS PUBLISHED AMAZON BASICS BUMPERS: https://www.ebay.co.uk/itm/"+str(lid),flush=True)
    print("PRICE GBP",PRICE,"QTY",QTY,"CATEGORY",CATEGORY,flush=True)
if __name__=="__main__":
    try: main()
    except (DraftError,ValueError,KeyError,TypeError,OSError) as exc:
        print("PUBLISH STOPPED:",str(exc),file=sys.stderr)
        sys.exit(1)
