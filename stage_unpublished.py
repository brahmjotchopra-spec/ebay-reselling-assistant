"""Stage a single NON-LIVE eBay UK inventory offer (quantity 0). Never publishes."""
import json
import os
import sys
from pathlib import Path
from ebay_client import DraftError, Inventory, get_token

SKU = "CAR-46787"
CATEGORY = "262204"  # Sun & Privacy Shades (vehicle)
STAGE_SKU = "DRAFT-" + SKU

def run():
    items = json.loads(Path(__file__).with_name("listings.json").read_text("utf-8"))
    rows = [x for x in items if x.get("sku") == SKU]
    if len(rows) != 1:
        raise DraftError("Expected exactly one staged SKU.")
    row = rows[0]
    if row.get("approved_for_unpublished_offer") is True:
        raise DraftError("This script is for unverified, non-live staging only.")
    if not row.get("title") or not row.get("description"):
        raise DraftError("Product details missing.")
    api = Inventory(get_token())
    print("STEP: verify read permission", flush=True)
    api.check_access()
    print("STEP: inspect existing inventory item", flush=True)
    existing = api.item(STAGE_SKU)
    print("STEP: inspect existing offers", flush=True)
    offers = api.offers(STAGE_SKU)
    inventory = {
        "product": {
            "title": row["title"],
            "description": row["description"],
            "imageUrls": [
                "https://www.godropship.co.uk/uploadfile/images/598808/2025-03/2025-03-05CR-tsgpdot8yn.jpg"
            ],
            "aspects": {
                "Brand": ["Unbranded"],
                "Type": ["Windscreen Cover"],
                "Colour": ["Silver"],
                "Material": ["Cotton, Aluminium Film"],
                "Placement on Vehicle": ["Front"],
                "Size": ["150 x 70 cm"],
            }
        },
        "condition": "NEW",
        "availability": {"shipToLocationAvailability": {"quantity": 0}},
    }
    if offers:
        if len(offers) != 1 or offers[0].get("status") != "UNPUBLISHED":
            raise DraftError("SKU exists in an unexpected offer state. Nothing changed.")
        if existing is None or existing.get("sku") != STAGE_SKU:
            raise DraftError("Missing inventory for existing offer.")
        if existing.get("availability", {}).get("shipToLocationAvailability", {}).get("quantity") != 0:
            raise DraftError("Existing inventory quantity not zero; refusing changes.")
        if not existing.get("product", {}).get("imageUrls"):
            print("STEP: enrich NON-LIVE inventory with supplier image and specifics", flush=True)
            api.create_item(STAGE_SKU, inventory)
        print("Existing NON-LIVE eBay offer found for SKU " + STAGE_SKU)
        print("Offer ID:", offers[0].get("offerId", "not returned"))
        return
    if existing is not None:
        if existing.get("sku") != STAGE_SKU or (
            existing.get("product", {}).get("title") != row["title"]
        ):
            raise DraftError("Conflicting existing inventory item, no changes made.")
        print("Reusing existing stock-zero inventory item.")
    else:
        print("STEP: create stock-zero inventory item", flush=True)
        api.create_item(STAGE_SKU, inventory)
        print("Created NON-LIVE inventory item with zero available stock.")
    offer = {
        "sku": STAGE_SKU,
        "marketplaceId": "EBAY_GB",
        "format": "FIXED_PRICE",
        "availableQuantity": 0,
        "categoryId": CATEGORY,
        "listingDescription": row["description"],
        "pricingSummary": {"price": {"value": row["price_gbp"], "currency": "GBP"}},
    }
    print("STEP: create unpublished offer", flush=True)
    offer_id = api.create_offer(offer)
    print("STEP: verify unpublished offer", flush=True)
    check = api.offer(offer_id)
    if check.get("status") != "UNPUBLISHED" or check.get("listing"):
        raise DraftError("Unexpected offer state; investigate before proceeding.")
    print("Created and checked NON-LIVE eBay offer. Offer ID:", offer_id)
    print("Not published; quantity 0, no fulfilment promised, no supplier order.")

if __name__ == "__main__":
    try:
        run()
    except (DraftError, OSError, ValueError) as exc:
        print("STAGING FAILED:", str(exc), file=sys.stderr)
        sys.exit(1)
