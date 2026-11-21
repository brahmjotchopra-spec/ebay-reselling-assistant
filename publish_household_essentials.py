"""Publish exactly one stocked pack of each of three previously staged eBay UK household essentials.

User confirmed physical possession of all three products on 21 Nov 2026.
No supplier orders, no dropshipping, no duplicate offers, no changes to prior
live listings. Illustrations are original but need seller verification against
actual stock; image disclosure is included in each description.
"""
import json,sys,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from ebay_client import Inventory,DraftError,get_token

ROOT="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/"
SOURCE=Path("research/household-essentials-stage.json")
TARGETS={
    "HOME-MICROFIBRE20":{
        "image":"household-microfibre-20.jpg",
        "title":"20 Pack Microfibre Cleaning Cloths Reusable Home Kitchen Bathroom Car",
        "description":(
            "One pack containing 20 reusable microfibre cleaning cloths for general household,"
            " kitchen, bathroom and vehicle cleaning. Washable and reusable for everyday cleaning."
            " You receive 20 cloths only; no sprays, tools or other accessories."
            " Main image is an original digital illustration of microfibre cloths, not a"
            " photograph of the exact stock; colours and folding may vary."
        ),
        "aspects":{"Type":["Cleaning Cloth"],"Material":["Microfibre"],"Number in Pack":["20"]},
    },
    "HOME-AIRFRYER100":{
        "image":"household-air-fryer-liners-100.jpg",
        "title":"100 Disposable Brown Paper Air Fryer Liners 7.9in Square 20cm",
        "description":(
            "A pack of 100 disposable brown bowl-style parchment paper liners for a suitably"
            " sized air fryer or oven tray. Nominal base size approximately 20cm (7.9in)."
            " Always check that the basket and liner dimensions suit your appliance."
            " IMPORTANT SAFETY: Never put empty liners into a preheating or running air fryer."
            " Ensure food weighs the liner securely down so it cannot touch heating elements."
            " You receive 100 paper liners only; food and air fryer not included."
            " Main image is an original digital illustration of this kind of liner,"
            " not a photograph of the exact stock."
        ),
        "aspects":{"Type":["Air Fryer Paper Liner"],"Material":["Paper"],"Colour":["Brown"],"Number in Pack":["100"]},
    },
    "HOME-DRAINCATCH100":{
        "image":"household-drain-hair-catchers-100.jpg",
        "title":"100 Disposable Shower Drain Hair Catcher Adhesive Mesh Stickers Filter",
        "description":(
            "One pack of 100 disposable adhesive mesh hair catchers designed for suitable"
            " flat bath and shower drain surroundings. Apply to a clean, dry surface."
            " Mesh filters help collect loose hair before it enters the drain."
            " Ensure your drain shape and size are compatible before ordering."
            " You receive 100 mesh hair-catcher stickers only; other contents not included."
            " Main image is an original digital illustration of this product type,"
            " not a photograph of the exact stock."
        ),
        "aspects":{"Type":["Drain Strainer"],"Features":["Disposable","Adhesive"],"Number in Pack":["100"]},
    },
}
QTY=1
def photo_ok(url):
    for _ in range(12):
        try:
            req=Request(url,method="GET",headers={"User-Agent":"Mozilla/5.0"})
            with urlopen(req,timeout=15) as resp:
                data=resp.read(3)
                if resp.status==200 and data==bytes.fromhex("ffd8ff") and "image/jpeg" in resp.headers.get("Content-Type",""):
                    return
        except (HTTPError,URLError,OSError):
            pass
        time.sleep(3)
    raise DraftError("Photo not publicly available yet: "+url)

def main():
    rows=json.loads(SOURCE.read_text(encoding="utf-8"))
    if not isinstance(rows,list) or len(rows)!=3 or {r.get("sku") for r in rows}!=set(TARGETS):
        raise DraftError("Candidate list unexpected")
    # Verify all images and draft identities before modifying any listings.
    for cfg in TARGETS.values():
        photo_ok(ROOT+cfg["image"])
    api=Inventory(get_token())
    api.check_access()
    states=[]
    for row in rows:
        rawsku=row["sku"]
        sku="DRAFT-"+rawsku
        offers=api.offers(sku)
        if len(offers)!=1:
            raise DraftError("Expected exactly one existing staged offer for "+sku)
        offer=api.offer(offers[0]["offerId"])
        item=api.item(sku)
        if not item or item.get("sku")!=sku or item.get("condition")!="NEW":
            raise DraftError("Inventory missing or wrong condition for "+sku)
        if offer.get("sku")!=sku or offer.get("categoryId")!=row["category_id"]:
            raise DraftError("Offer identity or category mismatch for "+sku)
        price=(offer.get("pricingSummary") or {}).get("price") or {}
        if price.get("currency")!="GBP" or str(price.get("value"))!=row["price_gbp"]:
            raise DraftError("Unapproved price or currency for "+sku)
        if offer.get("status")=="PUBLISHED":
            listing_id=str((offer.get("listing") or {}).get("listingId") or "")
            if not listing_id:
                raise DraftError("Published offer lacks listing ID: "+sku)
            print("ALREADY LIVE (no duplicate) "+rawsku+" https://www.ebay.co.uk/itm/"+listing_id,flush=True)
            continue
        if offer.get("status")!="UNPUBLISHED" or offer.get("listing"):
            raise DraftError("Unexpected eBay offer state for "+sku)
        if not (item.get("product") or {}).get("title","").startswith(row["title"][:28]):
            raise DraftError("Product identity mismatch for "+sku)
        stock=(item.get("availability") or {}).get("shipToLocationAvailability") or {}
        if stock.get("quantity") not in (0,1) or offer.get("availableQuantity") not in (0,1):
            raise DraftError("Unexpected stock counts for "+sku)
        policies=offer.get("listingPolicies") or {}
        if not all(policies.get(x) for x in ("paymentPolicyId","returnPolicyId","fulfillmentPolicyId")):
            raise DraftError("Seller policies missing for "+sku)
        location=offer.get("merchantLocationKey")
        if not location:raise DraftError("Dispatch origin missing for "+sku)
        states.append((row,sku,offer,item,policies,location))
    print("PREFLIGHT OK; non-live offers eligible:",len(states),flush=True)
    for row,sku,offer,item,policies,location in states:
        cfg=TARGETS[row["sku"]]
        product=dict(item.get("product") or {})
        product["title"]=cfg["title"]
        product["description"]=cfg["description"]
        product["aspects"]=cfg["aspects"]
        product["imageUrls"]=[ROOT+cfg["image"]]
        inventory={
            "product":product,"condition":"NEW",
            "availability":{"shipToLocationAvailability":{"quantity":QTY}}
        }
        api.create_item(sku,inventory)
        check=api.item(sku)
        if (check.get("product",{}).get("imageUrls")!=[ROOT+cfg["image"]]
            or check.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=QTY):
            raise DraftError("Image or quantity failed read-back for "+sku)
        payload={
            "sku":sku,"marketplaceId":"EBAY_GB","format":"FIXED_PRICE",
            "categoryId":row["category_id"],"availableQuantity":QTY,
            "listingDuration":offer.get("listingDuration") or "GTC",
            "listingDescription":cfg["description"],
            "pricingSummary":{"price":{"value":row["price_gbp"],"currency":"GBP"}},
            "listingPolicies":policies,"merchantLocationKey":location
        }
        api._request("PUT","/offer/"+offer["offerId"],payload)
        check_offer=api.offer(offer["offerId"])
        if check_offer.get("status")!="UNPUBLISHED" or check_offer.get("availableQuantity")!=QTY:
            raise DraftError("Offer readback failed for "+sku)
        try:
            published=api._request("POST","/offer/"+offer["offerId"]+"/publish")
        except Exception as exc:
            print("FAILED TO PUBLISH "+sku+": "+str(exc),flush=True)
            continue
        listing_id=str(published.get("listingId") or "")
        if not listing_id:
            print("UNCERTAIN PUBLISH RESULT "+sku+": no listingId; inspect server",flush=True)
            continue
        verified=api.offer(offer["offerId"])
        if (verified.get("status")=="PUBLISHED" and
            str((verified.get("listing") or {}).get("listingId"))==listing_id):
            print("SUCCESS PUBLISHED "+row["sku"]+" £"+row["price_gbp"]+
                  " QTY 1 URL https://www.ebay.co.uk/itm/"+listing_id,flush=True)
        else:
            print("NEEDS REVIEW "+sku+": publish response "+listing_id+" but status could not be verified",flush=True)
    print("PUBLICATION ATTEMPTS FINISHED. Check per-SKU statuses above; not a blanket success assertion.",flush=True)
if __name__=="__main__":
    try:main()
    except (DraftError,ValueError,OSError,KeyError,TypeError) as exc:
        print("HOUSEHOLD PUBLISH STOPPED:",exc,file=sys.stderr)
        sys.exit(1)
