"""Stage ONE reusable pet-hair/lint cleaning brush on eBay UK, with zero available stock.

The selected Amazon supplier URL and user's physical possession have NOT been
confirmed. This action creates an UNPUBLISHED offer only; it will never
publish, increase quantity, buy a product, or modify existing live listings.

Resale price is provisional: similar single brushes are advertised at much
lower prices and fees/postage/profit have not been validated.
"""
import sys
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-HOME-PETHAIRBRUSH-1"
CATEGORY="170626"  # eBay UK: Lint Removers
PRICE="8.99"  # unverified provisional test price, NOT a confirmed margin
TITLE="NTEK Reusable Pet Hair Remover Lint Cleaning Brush Sofa Carpet Clothes"
DESCRIPTION=(
    "One reusable pet hair and lint cleaning brush for use on suitable sofas, "
    "upholstery, car seats, carpets, pet bedding and clothing. This offer is "
    "for one manual cleaning brush only, with no additional accessories. "
    "Test on a small hidden area before using on delicate or loosely woven fabrics. "
    "Product colour, dimensions, the exact Amazon supplier item and product images "
    "must be checked against the item before this offer can be published."
)
REFERENCE_SKU="DRAFT-AMZ-RINGS-25MM-50"
POLICY_KEYS=("paymentPolicyId","returnPolicyId","fulfillmentPolicyId")

def main():
    api=Inventory(get_token())
    api.check_access()
    reference=api.offers(REFERENCE_SKU)
    if len(reference)!=1:
        raise DraftError("Cannot establish exactly one live seller-policy reference")
    ref=api.offer(reference[0]["offerId"])
    policies=ref.get("listingPolicies") or {}
    location=ref.get("merchantLocationKey")
    if (ref.get("status")!="PUBLISHED" or not location or
        not all(policies.get(x) for x in POLICY_KEYS)):
        raise DraftError("The reference offer lacks confirmed seller policies/location")
    policy_values={k:policies[k] for k in POLICY_KEYS}
    locations=api._request("GET","/location?limit=100").get("locations") or []
    if not any(x.get("merchantLocationKey")==location and
               x.get("merchantLocationStatus")=="ENABLED" for x in locations):
        raise DraftError("Seller dispatch location not enabled")

    expected_product={
        "title":TITLE,
        "description":DESCRIPTION,
        "brand":"NTEK",
        "mpn":"PHR-BL",
        "aspects":{
            "Brand":["NTEK"],
            "MPN":["PHR-BL"],
            "Type":["Lint Remover"],
            "Features":["Reusable"],
            "Number in Pack":["1"],
        },
    }
    existing=api.item(SKU)
    offers=api.offers(SKU)
    if len(offers)>1:
        raise DraftError("Ambiguous existing offer SKU; refuse duplicate")
    if existing:
        product=existing.get("product") or {}
        if (existing.get("sku")!=SKU or
            existing.get("condition")!="NEW" or
            product.get("title")!=TITLE or
            product.get("brand")!="NTEK" or
            product.get("mpn")!="PHR-BL" or
            product.get("imageUrls") or
            (existing.get("availability") or {}).get("shipToLocationAvailability",{}).get("quantity")!=0):
            raise DraftError("Existing inventory differs from the approved zero-stock draft")
    elif offers:
        raise DraftError("Offer exists but no corresponding inventory item")
    else:
        item={
            "product":expected_product,
            "condition":"NEW",
            "availability":{"shipToLocationAvailability":{"quantity":0}},
        }
        api.create_item(SKU,item)
        print("CREATED NON-SELLABLE INVENTORY RECORD",SKU,flush=True)

    if offers:
        offer=api.offer(offers[0]["offerId"])
        if offer.get("status")=="PUBLISHED":
            print("ALREADY PUBLISHED, NO CHANGES MADE",flush=True)
            return
        if offer.get("status")!="UNPUBLISHED" or offer.get("listing"):
            raise DraftError("Unexpected offer state; refuse update")
        offer_id=offer["offerId"]
    else:
        payload={
            "sku":SKU,
            "marketplaceId":"EBAY_GB",
            "format":"FIXED_PRICE",
            "categoryId":CATEGORY,
            "availableQuantity":0,
            "listingDescription":DESCRIPTION,
            "pricingSummary":{"price":{"value":PRICE,"currency":"GBP"}},
            "listingPolicies":policy_values,
            "merchantLocationKey":location,
            "listingDuration":"GTC"
        }
        offer_id=api.create_offer(payload)
        print("CREATED SINGLE-PRODUCT EBAY OFFER",offer_id,flush=True)

    checked=api.offer(offer_id)
    stored=api.item(SKU)
    price=(checked.get("pricingSummary") or {}).get("price") or {}
    if (checked.get("status")!="UNPUBLISHED" or checked.get("listing") or
        checked.get("sku")!=SKU or checked.get("categoryId")!=CATEGORY or
        checked.get("availableQuantity")!=0 or
        price.get("value")!=PRICE or price.get("currency")!="GBP" or
        stored.get("product",{}).get("title")!=TITLE or
        stored.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=0):
        raise DraftError("eBay offer verification failed; inspect before retry")
    print("VERIFIED SINGLE ITEM UNPUBLISHED EBAY OFFER",flush=True)
    print("SKU",SKU,"CATEGORY",CATEGORY,"PRICE GBP",PRICE,flush=True)
    print("QUANTITY ZERO. NO LIVE LISTING. NO BUYER CAN ORDER.",flush=True)
    print("PUBLISH BLOCKERS: physical stock ownership, exact-item images, shipping/margin and supplier match.",flush=True)

if __name__=="__main__":
    try:
        main()
    except (DraftError,ValueError,TypeError,KeyError,OSError) as exc:
        print("SINGLE BRUSH STAGING STOPPED:",exc,file=sys.stderr)
        sys.exit(1)
