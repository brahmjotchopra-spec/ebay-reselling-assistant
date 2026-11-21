"""Safely stage a single compact 32-in-1 precision screwdriver kit as an
UNPUBLISHED UK eBay offer with ZERO stock. This script never publishes, orders
stock, edits live offers or changes other SKUs. Supplier checkout, exact
images, packaging dimensions, fulfilment and profitability are not verified.
"""
import sys
from ebay_client import Inventory, DraftError, get_token

SKU = "DRAFT-AMZ-PRECISION-SCREW32-1"
REFERENCE_SKU = "DRAFT-AMZ-RINGS-25MM-50"
CATEGORY = "42255"  # eBay GB taxonomy verified 2026-11-21: Screwdrivers & Nutdrivers
PRICE = "7.49"  # Provisional, other listings cheaper; not a validated profitable price
TITLE = "32 in 1 Precision Screwdriver Set Magnetic Mini Repair Kit Phone Laptop Watch"
DESCRIPTION = (
    "One compact 32-in-1 precision screwdriver set with interchangeable bits "
    "for suitable small screws and everyday small-item repairs. "
    "Can be used for compatible electronics, spectacles, watches, "
    "laptops and other devices. Always check screw head type and size before use. "
    "You receive one screwdriver kit only, not any device shown for illustration. "
    "Exact included bits, case, materials, colour and dimensions must be "
    "checked against the received product before this draft is made available."
)
POLICY_KEYS = ("paymentPolicyId", "returnPolicyId", "fulfillmentPolicyId")

def main():
    api = Inventory(get_token())
    api.check_access()
    refs = api.offers(REFERENCE_SKU)
    if len(refs) != 1:
        raise DraftError("Unique published seller policy reference not found")
    ref = api.offer(refs[0]["offerId"])
    policies = ref.get("listingPolicies") or {}
    location = ref.get("merchantLocationKey")
    if ref.get("status") != "PUBLISHED" or not location or not all(policies.get(k) for k in POLICY_KEYS):
        raise DraftError("Published reference seller policies/location not verified")
    policy_values = {k: policies[k] for k in POLICY_KEYS}
    locations = api._request("GET", "/location?limit=100").get("locations") or []
    if not any(x.get("merchantLocationKey") == location and x.get("merchantLocationStatus") == "ENABLED" for x in locations):
        raise DraftError("Dispatch location is not enabled")

    item = api.item(SKU)
    offers = api.offers(SKU)
    if len(offers) > 1:
        raise DraftError("Multiple SKU offers, refuse duplicate")
    if item:
        product = item.get("product") or {}
        quantity = ((item.get("availability") or {}).get("shipToLocationAvailability") or {}).get("quantity")
        if (item.get("sku") != SKU or item.get("condition") != "NEW" or
            product.get("title") != TITLE or product.get("imageUrls") or quantity != 0):
            raise DraftError("Existing inventory mismatch, refuse changes")
    elif offers:
        raise DraftError("Offer without inventory item, refusing unsafe repair")
    else:
        api.create_item(SKU, {
            "product": {
                "title": TITLE,
                "description": DESCRIPTION,
                "aspects": {
                    "Type": ["Precision Screwdriver Set"],
                    "Number of Pieces": ["32"],
                    "Features": ["Magnetic", "Interchangeable Bits"]
                }
            },
            "condition": "NEW",
            "availability": {"shipToLocationAvailability": {"quantity": 0}}
        })
        print("CREATED zero-stock nonsellable screwdriver inventory item", flush=True)

    if offers:
        offer = api.offer(offers[0]["offerId"])
        if offer.get("status") == "PUBLISHED":
            print("EXISTING LISTING LIVE; NO CHANGES OR DUPLICATE", flush=True)
            return
        if offer.get("status") != "UNPUBLISHED" or offer.get("listing"):
            raise DraftError("Unexpected offer state; refuse modification")
        if (offer.get("sku") != SKU or offer.get("categoryId") != CATEGORY or
            offer.get("availableQuantity") != 0 or
            (offer.get("pricingSummary") or {}).get("price", {}).get("value") != PRICE):
            raise DraftError("Existing offer differs from planned candidate")
        offer_id = offers[0]["offerId"]
    else:
        offer_id = api.create_offer({
            "sku": SKU,
            "marketplaceId": "EBAY_GB",
            "format": "FIXED_PRICE",
            "categoryId": CATEGORY,
            "availableQuantity": 0,
            "listingDescription": DESCRIPTION,
            "listingDuration": "GTC",
            "pricingSummary": {"price": {"value": PRICE, "currency": "GBP"}},
            "listingPolicies": policy_values,
            "merchantLocationKey": location
        })
        print("CREATED 32-in-1 screwdriver nonlive offer", offer_id, flush=True)

    checked = api.offer(offer_id)
    stored = api.item(SKU)
    price = (checked.get("pricingSummary") or {}).get("price") or {}
    inventory_qty = ((stored.get("availability") or {}).get("shipToLocationAvailability") or {}).get("quantity")
    if (checked.get("status") != "UNPUBLISHED" or checked.get("listing") or
        checked.get("sku") != SKU or checked.get("categoryId") != CATEGORY or
        checked.get("availableQuantity") != 0 or
        price.get("currency") != "GBP" or str(price.get("value")) != PRICE or
        stored.get("product", {}).get("title") != TITLE or inventory_qty != 0):
        raise DraftError("eBay read-back did not verify zero-stock unpublished offer")
    print("SUCCESS: UNPUBLISHED EBAY OFFER", offer_id, "SKU", SKU,
          "PRICE GBP", PRICE, "STOCK 0", flush=True)
    print("No live listing. Confirm genuine stock, product images, postage and demand before publishing.", flush=True)

if __name__ == "__main__":
    try:
        main()
    except (DraftError, ValueError, TypeError, KeyError, OSError) as exc:
        print("SCREWDRIVER STAGING FAILED:", exc, file=sys.stderr)
        sys.exit(1)
