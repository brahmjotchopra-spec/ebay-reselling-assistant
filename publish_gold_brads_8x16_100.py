"""Publish one owner-confirmed 100-piece pack of 8x16mm gold split-pin craft brads.
The user confirmed owning the stock and asked to publish it on 22 Nov 2026.
Uses the exact six gallery images generated from the user's reference product.
Never buys stock or sends Amazon orders directly to eBay buyers.
Idempotent: one SKU, at most one existing offer; no duplicate publication.
"""
import sys,time
from urllib.request import Request,urlopen
from urllib.error import HTTPError, URLError
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-GOLD-BRADS-8X16-100-1"
CATEGORY="83990" # eBay UK: Scrapbooking & Paper Crafts > Decorative Brads
TITLE="100 Gold Split Pins Paper Fasteners 8mm x 16mm Mini Brads Scrapbooking Craft"
PRICE="7.99"
QTY=1
REF_SKU="DRAFT-HOME-MICROFIBRE20"
BASE="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/gold-brads/"
NAMES=[
 "01-main-100-gold-brads.jpg",
 "02-dimensions-8x16mm.jpg",
 "03-detail-split-prongs.jpg",
 "04-craft-use.jpg",
 "05-original-reference-product.jpg",
 "06-botanical-paper-in-use.jpg",
]
PHOTOS=[BASE+name for name in NAMES]
DESCRIPTION=(
 "ONE pack of 100 gold-colour mini split-pin paper fasteners (decorative brads). "
 "Rounded domed head approximately 8mm wide; overall pin length approximately 16mm. "
 "Each paper fastener has two bendable metal legs: insert through paper, cardstock "
 "or similar light craft materials and spread the legs on the reverse to hold in place. "
 "Useful for scrapbooking, handmade greeting cards, craft albums, paper decorations, "
 "and stationery projects. Gold-coloured finish, not solid gold; no claim of gold plating. "
 "100 fasteners included only. Papers, cards, tools and other props are not included. "
 "The gallery contains original digitally created product illustrations, together with "
 "a cropped reference product image; it does not depict photographs of the actual stock. "
 "Appearance, finish and lighting may vary slightly from the delivered product. "
 "Keep small parts away from children; pointed metal legs may be sharp."
)
POLICY_KEYS=("paymentPolicyId","returnPolicyId","fulfillmentPolicyId")

def images_check():
    for url in PHOTOS:
        for attempt in range(6):
            try:
                req=Request(url,headers={"User-Agent":"Mozilla/5.0"},method="GET")
                with urlopen(req,timeout=15) as f:
                    if (f.status==200 and f.headers.get("Content-Type","").startswith("image/jpeg")
                        and f.read(3)==bytes.fromhex("ffd8ff")):
                        break
            except (HTTPError,URLError,OSError):
                pass
            time.sleep(2)
        else:
            raise DraftError("Gallery JPEG inaccessible: "+url)
    print("SIX PUBLIC GALLERY IMAGES VERIFIED",flush=True)

def main():
    images_check()
    api=Inventory(get_token())
    api.check_access()
    offers=api.offers(SKU)
    if len(offers)>1:
        raise DraftError("More than one SKU offer: refuse any changes")
    old_offer=api.offer(offers[0]["offerId"]) if offers else None
    if old_offer:
        if old_offer.get("status")=="PUBLISHED":
            lid=(old_offer.get("listing") or {}).get("listingId")
            if not lid: raise DraftError("SKU live but listing ID missing")
            print("ALREADY PUBLISHED NO DUPLICATE https://www.ebay.co.uk/itm/"+str(lid),flush=True)
            return
        if old_offer.get("status")!="UNPUBLISHED" or old_offer.get("listing") or old_offer.get("sku")!=SKU:
            raise DraftError("Unexpected existing offer state")
        old_price=(old_offer.get("pricingSummary") or {}).get("price") or {}
        if str(old_price.get("value"))!=PRICE or old_price.get("currency")!="GBP" or old_offer.get("categoryId")!=CATEGORY:
            raise DraftError("Existing offer differs in price/category")
    previous=api.item(SKU)
    if previous:
        product=previous.get("product") or {}
        stock=(previous.get("availability") or {}).get("shipToLocationAvailability") or {}
        if product.get("title")!=TITLE or stock.get("quantity") not in (0,1):
            raise DraftError("Existing inventory differs; refuse to overwrite")
        if product.get("imageUrls") and product["imageUrls"]!=PHOTOS:
            raise DraftError("Existing gallery mismatch")
    ref=api.offers(REF_SKU)
    if len(ref)!=1:
        raise DraftError("Cannot determine single seller policy reference")
    live=api.offer(ref[0]["offerId"])
    if live.get("status")!="PUBLISHED":
        raise DraftError("Seller policy reference not published")
    policies=live.get("listingPolicies") or {}
    location=live.get("merchantLocationKey")
    if not location or not all(policies.get(k) for k in POLICY_KEYS):
        raise DraftError("Seller policies or dispatch location missing")
    locations=api._request("GET","/location?limit=100").get("locations") or []
    if not any(loc.get("merchantLocationKey")==location and loc.get("merchantLocationStatus")=="ENABLED" for loc in locations):
        raise DraftError("Dispatch location disabled")

    product={
        "title":TITLE,
        "description":DESCRIPTION,
        "imageUrls":PHOTOS,
        "aspects":{
            "Type":["Decorative Brads"],
            "Colour":["Gold"],
            "Material":["Metal"],
            "Size":["8 mm head x 16 mm overall"],
            "Number in Pack":["100"],
        },
    }
    api.create_item(SKU,{"product":product,"condition":"NEW",
        "availability":{"shipToLocationAvailability":{"quantity":QTY}}})
    readback=api.item(SKU)
    if (readback.get("product",{}).get("imageUrls")!=PHOTOS or
        readback.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=QTY or
        readback.get("product",{}).get("title")!=TITLE):
        raise DraftError("Inventory gallery, stock, or title failed verification")
    print("EBAY INVENTORY VERIFIED: 6 photos, quantity 1, £7.99 target",flush=True)
    offer_body={
        "sku":SKU,"marketplaceId":"EBAY_GB","format":"FIXED_PRICE",
        "categoryId":CATEGORY,"availableQuantity":QTY,
        "listingDuration":"GTC","listingDescription":DESCRIPTION,
        "pricingSummary":{"price":{"value":PRICE,"currency":"GBP"}},
        "listingPolicies":{k:policies[k] for k in POLICY_KEYS},
        "merchantLocationKey":location,
    }
    if old_offer:
        offer_id=old_offer["offerId"]
        api._request("PUT","/offer/"+offer_id,offer_body)
    else:
        offer_id=api.create_offer(offer_body)
    before=api.offer(offer_id)
    if (before.get("status")!="UNPUBLISHED" or before.get("listing") or
        before.get("availableQuantity")!=QTY or before.get("categoryId")!=CATEGORY or
        str((before.get("pricingSummary",{}).get("price") or {}).get("value"))!=PRICE):
        raise DraftError("Unexpected prepublish offer readback")
    result=api._request("POST","/offer/"+offer_id+"/publish")
    lid=result.get("listingId")
    if not lid:raise DraftError("Publish response missing listing ID; inspect eBay before rerun")
    published=api.offer(offer_id)
    if (published.get("status")!="PUBLISHED" or
        str((published.get("listing") or {}).get("listingId"))!=str(lid)):
        raise DraftError("Publish not verified in eBay readback")
    print("SUCCESS PUBLISHED GOLD BRADS https://www.ebay.co.uk/itm/"+str(lid),flush=True)
    print("PRICE £"+PRICE+" STOCK QTY "+str(QTY)+" PHOTO COUNT "+str(len(PHOTOS))+" OFFER ID "+str(offer_id),flush=True)
    print("Seller to dispatch one physical 100-pack within existing eBay handling time",flush=True)

if __name__=="__main__":
    try:main()
    except (DraftError,ValueError,TypeError,KeyError,OSError) as exc:
        print("GOLD BRADS PUBLISH STOPPED:",str(exc),file=sys.stderr)
        sys.exit(1)
