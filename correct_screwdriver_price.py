"""Correct one mispriced, confirmed-stock 32-in-1 precision screwdriver UK
listing. Seller confirmed actual purchase cost GBP 7.99 on 2026-11-21.
Price increases to provisional GBP 15.99; real postage, seller fees and
competitor viability still require review. NEVER modify other listings, create
new offers, or increase stock. Abort on identity/price mismatch.
"""
import sys
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-AMZ-PRECISION-SCREW32-1"
OFFER_ID="367603457011"
LISTING_ID="880140223664"
OLD="7.49"
NEW="15.99"

def main():
    api=Inventory(get_token())
    api.check_access()
    offers=api.offers(SKU)
    if len(offers)!=1 or offers[0].get("offerId")!=OFFER_ID:
        raise DraftError("Unique original screwdriver offer not found; no changes")
    current=api.offer(OFFER_ID)
    item=api.item(SKU)
    if not item or item.get("sku")!=SKU or item.get("condition")!="NEW":
        raise DraftError("Expected owned screwdriver inventory missing")
    live_id=str((current.get("listing") or {}).get("listingId") or "")
    if current.get("status")!="PUBLISHED" or current.get("sku")!=SKU or live_id!=LISTING_ID:
        raise DraftError("Listing status or public ID differs; no changes")
    price=(current.get("pricingSummary") or {}).get("price") or {}
    old_price=str(price.get("value"))
    if price.get("currency")!="GBP" or old_price not in (OLD,NEW):
        raise DraftError("Existing price unknown; refusing stale correction")
    if old_price==NEW:
        print("ALREADY CORRECTED: GBP",NEW,"https://www.ebay.co.uk/itm/"+LISTING_ID,flush=True)
        return
    payload={"requests":[{"offers":[{
        "offerId":OFFER_ID,
        "price":{"value":NEW,"currency":"GBP"}
    }]}]}
    result=api._request("POST","/bulk_update_price_quantity",payload)
    print("PRICE CORRECTION API RESPONSE",str(result).replace("'",'"')[:1800],flush=True)
    responses=result.get("responses")
    if not isinstance(responses,list) or not responses:
        raise DraftError("No update result; recheck eBay before retry")
    statuses=[]
    for response in responses:
        statuses.append(response.get("statusCode"))
        for offer in response.get("offers") or []:
            if offer.get("offerId")==OFFER_ID:
                statuses.append(offer.get("statusCode"))
                if offer.get("errors"):
                    raise DraftError("eBay returned validation errors for target offer")
    if any(s is not None and int(s)>=300 for s in statuses):
        raise DraftError("eBay reported a price update error")
    verified=api.offer(OFFER_ID)
    vp=(verified.get("pricingSummary") or {}).get("price") or {}
    if (verified.get("status")!="PUBLISHED" or
        str((verified.get("listing") or {}).get("listingId") or "")!=LISTING_ID or
        vp.get("currency")!="GBP" or str(vp.get("value"))!=NEW):
        raise DraftError("Updated live price did not verify; check before retry")
    print("SUCCESS VERIFIED SAME LIVE LISTING NEW PRICE GBP",NEW,
          "https://www.ebay.co.uk/itm/"+LISTING_ID,flush=True)
    print("Cost GBP 7.99, postage and fees still unverified, market comps lower.",flush=True)

if __name__=="__main__":
    try:
        main()
    except (DraftError, OSError, ValueError, TypeError, KeyError) as exc:
        print("LIVE PRICE CORRECTION FAILED:",exc,file=sys.stderr)
        sys.exit(1)
