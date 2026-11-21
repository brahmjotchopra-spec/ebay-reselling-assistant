"""Stage one researched Amazon-sourced candidate in eBay as a NONLIVE zero-stock offer.

This is NOT a published listing. Publish only after physical stock, photographs,
locker checkout, dispatch postage and current margins have been verified.
"""
import json
import os
import sys
from pathlib import Path

from ebay_bot import ensure_draft, payloads
from ebay_client import DraftError, Inventory, get_token

TARGET_SKU = "AMZ-RINGS-25MM-50"

def run():
    rows = json.loads(Path(__file__).with_name("listings.json").read_text("utf-8"))
    matched = [row for row in rows if row.get("sku") == TARGET_SKU]
    if len(matched) != 1:
        raise DraftError("Expected exactly one Amazon keyring candidate")
    row = matched[0]
    review = row.get("commercial_review", {})
    if row.get("approved_for_unpublished_offer") is not False or review.get("verified") is not False:
        raise DraftError("Unverified staging mode only; no approval flag permitted")
    if review.get("stock") != 0 or review.get("amazon_locker_verified") is not False:
        raise DraftError("Unverified and stock-zero conditions required")
    inv, offer = payloads(row)
    if inv["availability"]["shipToLocationAvailability"]["quantity"] != 0 or offer["availableQuantity"] != 0:
        raise DraftError("Refusing to stage any stock-positive offer")
    api = Inventory(get_token())
    api.check_access()
    state, offer_id = ensure_draft(api, inv, offer)
    print("Amazon keyrings: nonlive zero-stock offer " + state + ".")
    print("Unpublished eBay offer verified; no stock, no sales, no order placed.")
    # Keep IDs out of public GitHub logs.

if __name__ == "__main__":
    try:
        run()
    except (DraftError, OSError, ValueError) as ex:
        print("STAGING FAILED:", ex, file=sys.stderr)
        sys.exit(1)
