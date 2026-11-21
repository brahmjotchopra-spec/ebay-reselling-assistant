"""Stage three researched everyday essentials as zero-stock UNPUBLISHED eBay offers.

No confirmed physical inventory, packaging costs, delivery eligibility, image rights
or profit calculations for these three. This action never publishes anything,
never increments stock, and never changes previously live offers or gift tags.
It reuses existing seller payment, returns, postage, and location settings.
"""
import json
import sys
from pathlib import Path
from ebay_client import Inventory, DraftError, get_token
from ebay_bot import payloads, ensure_draft

SOURCE=Path("research/household-essentials-stage.json")
EXPECTED={
 "HOME-MICROFIBRE20":"29509",
 "HOME-AIRFRYER100":"25846",
 "HOME-DRAINCATCH100":"260554"
}
REFERENCE_SKU="DRAFT-AMZ-RINGS-25MM-50"
POLICY_KEYS=("paymentPolicyId","returnPolicyId","fulfillmentPolicyId")

def validate(rows):
    if not isinstance(rows,list) or len(rows)!=3 or {x["sku"] for x in rows}!=set(EXPECTED):
        raise DraftError("Unexpected household candidate set")
    for row in rows:
        sku=row["sku"]
        if (row["category_id"]!=EXPECTED[sku] or row.get("stock")!=0 or
            row.get("stock_owned_confirmed") is not False or
            row.get("postage_verified") is not False or
            row.get("supplier_exact_match_verified") is not False or
            row.get("image_urls")!=[] or
            row.get("price_status")!="unverified provisional"):
            raise DraftError("Unverified candidates can only be staged without photos and with quantity zero")
        inv,offer=payloads(row)
        if (inv["availability"]["shipToLocationAvailability"]["quantity"]!=0 or
            offer["availableQuantity"]!=0):
            raise DraftError("Candidate quantity is not zero")

def offer_matches(obj,row):
    expected_price=row["price_gbp"]
    price=(obj.get("pricingSummary") or {}).get("price") or {}
    return (obj.get("status")=="UNPUBLISHED"
            and not obj.get("listing")
            and obj.get("sku")=="DRAFT-"+row["sku"]
            and obj.get("categoryId")==row["category_id"]
            and obj.get("availableQuantity")==0
            and price.get("currency")=="GBP"
            and price.get("value")==expected_price)

def main():
    rows=json.loads(SOURCE.read_text(encoding="utf-8"))
    validate(rows)
    api=Inventory(get_token())
    api.check_access()
    reference=api.offers(REFERENCE_SKU)
    if len(reference)!=1:
        raise DraftError("One live keyring reference offer required to reuse policies")
    ref=api.offer(reference[0]["offerId"])
    policies=ref.get("listingPolicies") or {}
    location=ref.get("merchantLocationKey")
    if (ref.get("status")!="PUBLISHED" or not location or
        not all(policies.get(p) for p in POLICY_KEYS)):
        raise DraftError("Live reference seller policies missing")
    policies={p:policies[p] for p in POLICY_KEYS}
    locations=api._request("GET","/location?limit=100").get("locations") or []
    if not any(x.get("merchantLocationKey")==location and
               x.get("merchantLocationStatus")=="ENABLED" for x in locations):
        raise DraftError("Reference dispatch location not enabled")

    # Preflight all three existing SKU identities before making any changes.
    existing=[]
    for row in rows:
        sku="DRAFT-"+row["sku"]
        inventory=api.item(sku)
        offers=api.offers(sku)
        if offers:
            if len(offers)!=1 or inventory is None:
                raise DraftError("Conflicting offer state for "+sku)
            live=api.offer(offers[0]["offerId"])
            if not offer_matches(live,row):
                raise DraftError("Existing offer differs or is live: "+sku)
            if (inventory.get("product",{}).get("title")!=row["title"] or
                inventory.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=0 or
                inventory.get("condition")!="NEW"):
                raise DraftError("Existing stock item changed: "+sku)
            current_policies=live.get("listingPolicies") or {}
            if any(current_policies.get(key) not in (None,policies[key]) for key in POLICY_KEYS):
                raise DraftError("Existing business policies differ: "+sku)
            if live.get("merchantLocationKey") not in (None,location):
                raise DraftError("Existing merchant dispatch location differs: "+sku)
        elif inventory and (inventory.get("product",{}).get("title")!=row["title"] or
                          inventory.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=0):
            raise DraftError("Conflicting orphan inventory item: "+sku)
        existing.append((row,bool(offers)))

    for row,already in existing:
        inv,offer=payloads(row)
        sku=offer["sku"]
        if not already:
            state,offer_id=ensure_draft(api,inv,offer)
            print("STAGED NEW INVENTORY/OFFER:",sku,"state",state,flush=True)
        else:
            offer_id=api.offers(sku)[0]["offerId"]
            print("REUSED EXISTING UNPUBLISHED OFFER:",sku,flush=True)
        current=api.offer(offer_id)
        if not offer_matches(current,row):
            raise DraftError("Draft verification failed before policy attachment: "+sku)
        if current.get("listingPolicies")!=policies or current.get("merchantLocationKey")!=location:
            updated={**offer,
                     "listingDuration":current.get("listingDuration") or "GTC",
                     "listingPolicies":policies,
                     "merchantLocationKey":location}
            api._request("PUT","/offer/"+offer_id,updated)
        verified=api.offer(offer_id)
        inv_state=api.item(sku)
        if (not offer_matches(verified,row) or
            any((verified.get("listingPolicies") or {}).get(k)!=policies[k] for k in POLICY_KEYS) or
            verified.get("merchantLocationKey")!=location or
            inv_state.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=0):
            raise DraftError("eBay zero-stock/policy read-back failed for "+sku)
        print("CONFIRMED UNPUBLISHED:",sku,"OFFER_ID",offer_id,
              "GBP",row["price_gbp"],"AVAILABLE 0",
              "SUPPLIER/COST/PHOTOS STILL UNVERIFIED",flush=True)
    print("SUCCESS: THREE NEW ZERO-STOCK UNPUBLISHED EBAY OFFERS. NONE LIVE, NO CUSTOMER ORDERS POSSIBLE.",flush=True)
    print("Existing live listings remain unchanged. Kraft tags not touched.",flush=True)

if __name__=="__main__":
    try:main()
    except (DraftError,ValueError,KeyError,TypeError,OSError) as exc:
        print("EVERYDAY ESSENTIALS STAGING STOPPED:",exc,file=sys.stderr)
        sys.exit(1)
