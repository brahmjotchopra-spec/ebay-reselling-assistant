"""Stage one 120cm adjustable rubber pet-hair broom as an UNPUBLISHED zero-stock
eBay UK offer. Never sell, order, publish, or alter another product. Supplier
checkout, packed dimensions, genuine photographs, stock and net margin remain
unverified. This script can be safely rerun without creating a duplicate.
"""
import sys
from ebay_client import Inventory, DraftError, get_token

SKU = "DRAFT-AMZ-RUBBERBROOM-120CM-1"
REF = "DRAFT-AMZ-RINGS-25MM-50"
CATEGORY = "260133"
PRICE = "10.99"
TITLE = "Rubber Pet Hair Broom 120cm Adjustable Handle Squeegee Carpet Floor Brush"
DESCRIPTION = (
    "One rubber bristle cleaning broom with adjustable handle up to approximately "
    "120 cm and a built-in squeegee edge. Nominal broom head width 31 cm. "
    "For gathering pet hair and debris on suitable carpets, rugs and hard floors. "
    "You receive one broom and its handle only. No extra accessories included. "
    "Product colour, packed dimensions and exact manufacturer will be confirmed "
    "against the stock before this item is offered for sale."
)
KEYS = ("paymentPolicyId", "returnPolicyId", "fulfillmentPolicyId")

def main():
    api = Inventory(get_token())
    api.check_access()
    reference_offers = api.offers(REF)
    if len(reference_offers) != 1:
        raise DraftError("Unique live reference offer missing")
    reference = api.offer(reference_offers[0]["offerId"])
    policies = reference.get("listingPolicies") or {}
    location = reference.get("merchantLocationKey")
    if reference.get("status") != "PUBLISHED" or not location or not all(policies.get(k) for k in KEYS):
        raise DraftError("Reference lacks verified eBay seller policies and location")
    locations = api._request("GET", "/location?limit=100").get("locations") or []
    if not any(x.get("merchantLocationKey") == location and
               x.get("merchantLocationStatus") == "ENABLED" for x in locations):
        raise DraftError("Reference seller inventory location not enabled")
    policies = {key: policies[key] for key in KEYS}
    item = api.item(SKU)
    offers = api.offers(SKU)
    if len(offers) > 1:
        raise DraftError("Multiple offers for the product SKU: refusing duplicate")
    if item:
        product = item.get("product") or {}
        quantity = ((item.get("availability") or {}).get("shipToLocationAvailability") or {}).get("quantity")
        if product.get("title") != TITLE or item.get("condition") != "NEW" or quantity != 0 or product.get("imageUrls"):
            raise DraftError("Existing inventory conflicts; refusing modification")
    elif offers:
        raise DraftError("Existing offer has no matching inventory item")
    else:
        api.create_item(SKU, {
            "product": {
                "title": TITLE,
                "description": DESCRIPTION,
                "aspects": {
                    "Type": ["Broom"],
                    "Material": ["Rubber"],
                    "Features": ["Squeegee", "Adjustable Handle"]
                }
            },
            "condition": "NEW",
            "availability": {"shipToLocationAvailability": {"quantity": 0}}
        })
        print("Created non-sellable zero-stock inventory record", flush=True)
    if offers:
        existing = api.offer(offers[0]["offerId"])
        if existing.get("status") == "PUBLISHED":
            print("ALREADY LIVE: no modifications or duplicate", flush=True)
            return
        if existing.get("status") != "UNPUBLISHED" or existing.get("listing"):
            raise DraftError("Unexpected offer state")
        offer_id = offers[0]["offerId"]
    else:
        offer_id = api.create_offer({
            "sku": SKU,
            "marketplaceId": "EBAY_GB",
            "format": "FIXED_PRICE",
            "categoryId": CATEGORY,
            "availableQuantity": 0,
            "listingDuration": "GTC",
            "listingDescription": DESCRIPTION,
            "pricingSummary": {"price": {"value": PRICE, "currency": "GBP"}},
            "listingPolicies": policies,
            "merchantLocationKey": location
        })
        print("Created new nonlive offer", flush=True)
    offer = api.offer(offer_id)
    item = api.item(SKU)
    price = (offer.get("pricingSummary") or {}).get("price") or {}
    if (offer.get("sku") != SKU or offer.get("status") != "UNPUBLISHED" or
        offer.get("listing") or offer.get("categoryId") != CATEGORY or
        offer.get("availableQuantity") != 0 or price.get("currency") != "GBP" or
        str(price.get("value")) != PRICE or
        item.get("product", {}).get("title") != TITLE or
        ((item.get("availability") or {}).get("shipToLocationAvailability") or {}).get("quantity") != 0):
        raise DraftError("Offer/inventory read-back did not validate")
    print("SUCCESS: UNPUBLISHED EBAY OFFER", offer_id, "SKU", SKU,
          "PRICE GBP", PRICE, "STOCK 0", flush=True)
    print("No live listing. Physical stock, original images, packed size and postage still required.", flush=True)

if __name__ == "__main__":
    try:
        main()
    except (DraftError, OSError, KeyError, ValueError, TypeError) as exc:
        print("BROOM STAGING FAILED:", exc, file=sys.stderr)
        sys.exit(1)
