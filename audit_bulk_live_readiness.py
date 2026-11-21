"""Read-only readiness check for three stocked Amazon bulk eBay offers.

Never publishes, modifies inventory, or logs seller credentials.
"""
import json
import sys
from pathlib import Path
from ebay_client import Inventory, get_token, DraftError

TARGETS = {
    "BULK-JUMP-6MM-100",
    "BULK-GRIP-MIX-100",
    "BULK-TAGS-MIX-50",
}

def main():
    rows = json.loads(Path("research/amazon-bulk-stage.json").read_text("utf-8"))
    if len(rows) != 3 or {r["sku"] for r in rows} != TARGETS:
        raise DraftError("Unexpected candidate set")
    api = Inventory(get_token())
    api.check_access()
    all_ready = True
    for row in rows:
        sku = "DRAFT-" + row["sku"]
        item = api.item(sku)
        offers = api.offers(sku)
        if item is None or len(offers) != 1:
            print(sku + ": HOLD - one inventory item and one offer required")
            all_ready = False
            continue
        offer = api.offer(offers[0]["offerId"])
        images = item.get("product", {}).get("imageUrls") or []
        policies = offer.get("listingPolicies") or {}
        required_policies = ("paymentPolicyId", "returnPolicyId", "fulfillmentPolicyId")
        has_policies = all(bool(policies.get(k)) for k in required_policies)
        location = bool(offer.get("merchantLocationKey"))
        price = (offer.get("pricingSummary") or {}).get("price") or {}
        match = (item.get("product", {}).get("title") == row["title"] and
                 offer.get("categoryId") == row["category_id"] and
                 str(price.get("value")) == row["price_gbp"] and
                 price.get("currency") == "GBP")
        quantity = (item.get("availability") or {}).get("shipToLocationAvailability") or {}
        available = quantity.get("quantity", None)
        status = offer.get("status", "UNKNOWN")
        print(sku + ": " + status)
        print("  Product identity/price/category matching staged details:", match)
        print("  Listing product image count:", len(images))
        print("  Shipping/payment/returns policies:", "complete" if has_policies else "incomplete")
        print("  Dispatch location configured:", location)
        print("  Current inventory count on eBay:", available)
        print("  Offer quantity on eBay:", offer.get("availableQuantity"))
        if status == "PUBLISHED":
            print("  Live listing ID:", (offer.get("listing") or {}).get("listingId"))
        ready = (match and bool(images) and has_policies and location)
        if not ready or status != "PUBLISHED":
            all_ready = False
            print("  LIVE PUBLISHING GATE: not passed; no changes made")
    print("OVERALL:", "All offers live" if all_ready else "Publishing prerequisites outstanding")
    print("Stock possession is reported by user, but exact pack counts, genuine photos, packed dimensions and postage remain independently unverified.")

if __name__ == "__main__":
    try:
        main()
    except (DraftError, ValueError, KeyError, OSError) as exc:
        print("READ-ONLY EBAY AUDIT FAILED:", exc, file=sys.stderr)
        sys.exit(1)
