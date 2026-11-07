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
    api.check_access()
    offers = api.offers(STAGE_SKU)
    if offers:
        if len(offers) != 1 or offers[0].get("status") != "UNPUBLISHED":
            raise DraftError("SKU exists in an unexpected offer state. Nothing changed.")
        print("Existing NON-LIVE eBay offer found for SKU " + STAGE_SKU)
        print("Offer ID:", offers[0].get("offerId", "not returned"))
        return
    existing = api.item(STAGE_SKU)
    inventory = {
        "product": {"title": row["title"], "description": row["description"]},
        "condition": "NEW",
        "availability": {"shipToLocationAvailability": {"quantity": 0}},
    }
    if existing is not None:
        if existing.get("sku") != STAGE_SKU or (
            existing.get("product", {}).get("title") != row["title"]
        ):
            raise DraftError("Conflicting existing inventory item, no changes made.")
        print("Reusing existing stock-zero inventory item.")
    else:
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
    offer_id = api.create_offer(offer)
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
