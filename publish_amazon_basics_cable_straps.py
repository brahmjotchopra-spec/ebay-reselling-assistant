"""Publish the single owner-confirmed Amazon Basics 100 cable-strap pack.

User explicitly confirmed physically possessing the stock and requested publication
on 22 Nov 2026. Reuse offer 368646809011, never create an offer or buy stock.
Listing photographs are labelled as digitally created illustrations.
"""
import sys
from urllib.request import Request, urlopen
from ebay_client import Inventory, DraftError, get_token
from stage_amazon_basics_cable_straps import SKU, TITLE, PRICE, BASE, NAMES, DESCRIPTION

OFFER_ID="368646809011"
QTY=1
POLICY_FIELDS=("paymentPolicyId","returnPolicyId","fulfillmentPolicyId")
GALLERY=[BASE+name for name in NAMES]

def verify_images():
    if len(GALLERY)!=6 or len(set(GALLERY))!=6:
        raise DraftError("Six unique photos expected")
    for url in GALLERY:
        req=Request(url,headers={"User-Agent":"Mozilla/5.0"}, method="GET")
        with urlopen(req,timeout=18) as resp:
            if resp.status!=200 or not resp.headers.get("Content-Type","").startswith("image/jpeg") or resp.read(3)!=bytes.fromhex("ffd8ff"):
                raise DraftError("Photo is not a valid publicly accessible JPEG")

def main():
    verify_images()
    api=Inventory(get_token())
    api.check_access()
    offers=api.offers(SKU)
    if len(offers)!=1 or offers[0].get("offerId")!=OFFER_ID:
        raise DraftError("Unique expected eBay offer missing or changed; no duplicate")
    offer=api.offer(OFFER_ID)
    if offer.get("status")=="PUBLISHED":
        listing_id=(offer.get("listing") or {}).get("listingId")
        if not listing_id: raise DraftError("Already published but listing ID unavailable")
        print("ALREADY LIVE - NO DUPLICATE: https://www.ebay.co.uk/itm/"+str(listing_id),flush=True)
        return
    if offer.get("status")!="UNPUBLISHED" or offer.get("listing"):
        raise DraftError("Offer has unexpected state")
    if offer.get("sku")!=SKU or offer.get("marketplaceId")!="EBAY_GB" or offer.get("format")!="FIXED_PRICE":
        raise DraftError("Wrong offer identity, marketplace or format")
    price=(offer.get("pricingSummary") or {}).get("price") or {}
    if str(price.get("value"))!=PRICE or price.get("currency")!="GBP":
        raise DraftError("Price differs from reviewed £11.99 GBP; no publish")
    if offer.get("availableQuantity") not in (0,1):
        raise DraftError("Unexpected offer stock count")
    if not str(offer.get("categoryId") or "").isdigit():
        raise DraftError("Category missing")
    policies=offer.get("listingPolicies") or {}
    location=offer.get("merchantLocationKey")
    if not location or not all(policies.get(k) for k in POLICY_FIELDS):
        raise DraftError("Incomplete seller shipping/payment/return policy")
    locs=api._request("GET","/location?limit=100").get("locations") or []
    if not any(loc.get("merchantLocationKey")==location and loc.get("merchantLocationStatus")=="ENABLED" for loc in locs):
        raise DraftError("Merchant dispatch location disabled")
    item=api.item(SKU)
    if not item or item.get("sku")!=SKU or item.get("condition")!="NEW":
        raise DraftError("Item absent or condition changed")
    prod=item.get("product") or {}
    if prod.get("title")!=TITLE or prod.get("imageUrls")!=GALLERY or len(prod.get("imageUrls") or [])!=6:
        raise DraftError("Title or exact six-image gallery differs from approved images")
    if prod.get("description")!=DESCRIPTION or "digitally created illustrations" not in DESCRIPTION:
        raise DraftError("Digital illustration disclosure differs")
    stock=(item.get("availability") or {}).get("shipToLocationAvailability") or {}
    if stock.get("quantity") not in (0,1):
        raise DraftError("Unexpected inventory stock")
    if offer.get("listingDescription")!=DESCRIPTION:
        raise DraftError("Draft description changed: inspect before publishing")
    print("PREFLIGHT PASSED exact offer, six photos, enabled dispatch location, £11.99, qty one",flush=True)

    inv_payload={"product":prod,"condition":"NEW",
                 "availability":{"shipToLocationAvailability":{"quantity":QTY}}}
    api.create_item(SKU,inv_payload)
    item_checked=api.item(SKU)
    if ((item_checked.get("availability") or {}).get("shipToLocationAvailability") or {}).get("quantity")!=QTY or (item_checked.get("product") or {}).get("imageUrls")!=GALLERY:
        raise DraftError("Inventory stock/gallery verification failed")
    body={
        "sku":SKU,"marketplaceId":"EBAY_GB","format":"FIXED_PRICE",
        "categoryId":offer["categoryId"],"availableQuantity":QTY,
        "listingDuration":offer.get("listingDuration") or "GTC",
        "listingDescription":DESCRIPTION,
        "pricingSummary":{"price":{"value":PRICE,"currency":"GBP"}},
        "listingPolicies":{k:policies[k] for k in POLICY_FIELDS},
        "merchantLocationKey":location
    }
    api._request("PUT","/offer/"+OFFER_ID,body)
    before=api.offer(OFFER_ID)
    if (before.get("status")!="UNPUBLISHED" or before.get("listing") or
        before.get("availableQuantity")!=QTY or
        str(((before.get("pricingSummary") or {}).get("price") or {}).get("value"))!=PRICE):
        raise DraftError("Prepublish readback not as expected")

    result=api._request("POST","/offer/"+OFFER_ID+"/publish")
    listing_id=result.get("listingId")
    if not listing_id:
        raise DraftError("Publish response returned no listing ID. Investigate current offer state before retry")
    after=api.offer(OFFER_ID)
    if (after.get("status")!="PUBLISHED" or
        str((after.get("listing") or {}).get("listingId"))!=str(listing_id)):
        raise DraftError("Publish response is not verified in eBay readback")
    print("SUCCESS PUBLISHED https://www.ebay.co.uk/itm/"+str(listing_id),flush=True)
    print("VERIFIED £"+PRICE+" | quantity 1 | 6 exact gallery photos | offer "+OFFER_ID,flush=True)
    print("Reminder: Seller must dispatch personally from the confirmed physical stock within configured handling time",flush=True)

if __name__=="__main__":
    try: main()
    except (DraftError,ValueError,TypeError,KeyError,OSError) as exc:
        print("CABLE STRAPS PUBLISH STOPPED:",str(exc),file=sys.stderr)
        sys.exit(1)
