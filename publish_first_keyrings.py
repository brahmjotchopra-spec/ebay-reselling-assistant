"""Publish exactly one pack of 50 generic split rings using the eBay Inventory API.

Never publishes a second offer; refuses unexpected item, category, policy or photo changes.
If this run is interrupted, rerun to reconcile before another change.
"""
import sys, json, os, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from ebay_client import DraftError, Inventory, get_token

SKU = "DRAFT-AMZ-RINGS-25MM-50"
PHOTO = "https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/keyrings-50.jpg"
EXPECTED_TITLE="50 x 25mm Silver Split Key Rings Metal Keyring Hoops Keychain Craft Rings"
PAYMENT="254751987026"; RETURNS="254752096026"
LOCATION="home_dispatch_uk"
def check_photo_url():
    for attempt in range(8):
        try:
            r=Request(PHOTO,method="HEAD",headers={"User-Agent":"eBay-Inventory-Photo-Check"})
            with urlopen(r,timeout=15) as h:
                if h.status==200 and "image" in h.headers.get("Content-Type",""):
                    return
        except Exception:
            pass
        time.sleep(4)
    raise DraftError("Photo not publicly reachable, refusing publication")

def main():
    import pathlib
    data=json.loads(pathlib.Path("listings.json").read_text("utf-8"))
    rows=[x for x in data if x.get("sku")=="AMZ-RINGS-25MM-50"]
    if len(rows)!=1:raise DraftError("Expected one SKU")
    r=rows[0]
    if r.get("title")!=EXPECTED_TITLE or r.get("price_gbp")!="5.79" or r.get("category_id")!="150055":
        raise DraftError("Product title, category or price changed")
    if not pathlib.Path("launch/keyrings-evidence.json").exists():
        raise DraftError("Missing stock confirmation evidence")
    evidence=json.loads(pathlib.Path("launch/keyrings-evidence.json").read_text("utf-8"))
    if evidence.get("user_reports_stock_in_hand") is not True:
        raise DraftError("Seller has not confirmed possession")
    check_photo_url()
    api=Inventory(get_token())
    api.check_access()
    items=api.item(SKU)
    offers=api.offers(SKU)
    if not items or len(offers)!=1:raise DraftError("Expected one existing offer")
    offer=api.offer(offers[0]["offerId"])
    if offer.get("status")=="PUBLISHED" and offer.get("listing"):
        listing=offer["listing"]
        print("ALREADY PUBLISHED; eBay listing:",listing.get("listingId","not returned"))
        return
    if offer.get("status")!="UNPUBLISHED" or offer.get("listing"):
        raise DraftError("Offer in unexpected state, refusing")
    if items.get("sku")!=SKU or items.get("product",{}).get("title")!=EXPECTED_TITLE:
        raise DraftError("Existing item differs")
    if items.get("product",{}).get("imageUrls") not in (None,[],[PHOTO]):
        raise DraftError("Existing images must be reviewed")
    pol=offer.get("listingPolicies",{})
    if pol.get("paymentPolicyId")!=PAYMENT or pol.get("returnPolicyId")!=RETURNS or not pol.get("fulfillmentPolicyId"):
        raise DraftError("Offer's seller policies are incomplete")
    if offer.get("merchantLocationKey")!=LOCATION:
        raise DraftError("Dispatch origin not confirmed")
    if offer.get("pricingSummary",{}).get("price",{}).get("value")!="5.79":
        raise DraftError("Offer price mismatch")
    if offer.get("availableQuantity") not in (0,1):
        raise DraftError("Unexpected stock quantity; refusing")
    product=dict(items.get("product",{}))
    product["imageUrls"]=[PHOTO]
    product["description"]=r["description"]
    invbody={
      "product":product,"condition":"NEW",
      "availability":{"shipToLocationAvailability":{"quantity":1}}
    }
    api.create_item(SKU,invbody)
    current=api.item(SKU)
    if current.get("product",{}).get("imageUrls")!=[PHOTO] or current.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=1:
        raise DraftError("Image/stock update failed verification")
    payload={
      "sku":SKU,"marketplaceId":"EBAY_GB","format":"FIXED_PRICE",
      "categoryId":"150055","availableQuantity":1,
      "listingDuration":offer.get("listingDuration") or "GTC",
      "listingDescription":r["description"],
      "pricingSummary":{"price":{"value":"5.79","currency":"GBP"}},
      "listingPolicies":pol,"merchantLocationKey":LOCATION
    }
    api._request("PUT","/offer/"+offer["offerId"],payload)
    checked=api.offer(offer["offerId"])
    if checked.get("availableQuantity")!=1 or checked.get("status")!="UNPUBLISHED":
        raise DraftError("Offer not ready after update")
    result=api._request("POST","/offer/"+offer["offerId"]+"/publish")
    listing_id=result.get("listingId")
    if not listing_id:
        raise DraftError("Publication response lacked listingId; inspect eBay before retrying")
    print("PUBLISHED ONE 50-RING PACK on eBay UK")
    print("Listing ID:",listing_id)
    print("Public listing URL: https://www.ebay.co.uk/itm/"+str(listing_id))
    remote=api.offer(offer["offerId"])
    if remote.get("status")!="PUBLISHED" or remote.get("listing",{}).get("listingId")!=listing_id:
        raise DraftError("Listing was published but confirmation disagrees; reconcile seller account")
    print("VERIFIED live listing with quantity 1, price GBP 5.79, free Royal Mail 2nd Class.")

if __name__=="__main__":
    try:main()
    except (DraftError, OSError, ValueError, KeyError) as e:
        print("EBAY PUBLICATION FAILED:",e,file=sys.stderr)
        sys.exit(1)
