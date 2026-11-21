"""Attach existing seller business policies to three zero-stock, UNPUBLISHED bulk offers.

Reuses verified live keyring offer policy IDs and dispatch location.
Makes NO listings live, changes NO quantities, and does not alter live keyrings.
"""
import json
import sys
from pathlib import Path
from ebay_client import Inventory, DraftError, get_token

REFERENCE_SKU = "DRAFT-AMZ-RINGS-25MM-50"
EXPECTED = {"BULK-JUMP-6MM-100", "BULK-GRIP-MIX-100", "BULK-TAGS-MIX-50"}
POLICY_KEYS = ("paymentPolicyId", "returnPolicyId", "fulfillmentPolicyId")

def main():
    rows = json.loads(Path("research/amazon-bulk-stage.json").read_text("utf-8"))
    if len(rows) != 3 or {r["sku"] for r in rows} != EXPECTED:
        raise DraftError("Candidate set differs from approved three")
    api = Inventory(get_token())
    api.check_access()
    ref_offers = api.offers(REFERENCE_SKU)
    if len(ref_offers) != 1:
        raise DraftError("Cannot establish one reference keyring offer")
    ref = api.offer(ref_offers[0]["offerId"])
    policies = ref.get("listingPolicies") or {}
    location = ref.get("merchantLocationKey")
    if ref.get("status") != "PUBLISHED" or not location or not all(policies.get(k) for k in POLICY_KEYS):
        raise DraftError("Reference live listing is not suitable for reusing existing shipping/return/payment policies")
    policies = {k: policies[k] for k in POLICY_KEYS}
    locations = api._request("GET", "/location?limit=100").get("locations", [])
    if not any(x.get("merchantLocationKey") == location and x.get("merchantLocationStatus") == "ENABLED" for x in locations):
        raise DraftError("Reference dispatch location is not enabled")

    # Preflight every candidate before making any modifications.
    ready = []
    for row in rows:
        sku = "DRAFT-" + row["sku"]
        inv = api.item(sku)
        offers = api.offers(sku)
        if not inv or len(offers) != 1:
            raise DraftError("Missing or ambiguous inventory or offer for " + sku)
        offer = api.offer(offers[0]["offerId"])
        if offer.get("status") != "UNPUBLISHED" or offer.get("listing"):
            raise DraftError("Refusing to modify any live or unknown-status offer")
        if offer.get("sku") != sku or offer.get("categoryId") != row["category_id"]:
            raise DraftError("Wrong item category or SKU for " + sku)
        price = (offer.get("pricingSummary") or {}).get("price") or {}
        if price.get("value") != row["price_gbp"] or price.get("currency") != "GBP":
            raise DraftError("Unexpected price on " + sku)
        if inv.get("product", {}).get("title") != row["title"]:
            raise DraftError("Unexpected product title on " + sku)
        if (offer.get("availableQuantity") != 0 or
            inv.get("availability", {}).get("shipToLocationAvailability", {}).get("quantity") != 0):
            raise DraftError("Quantity changed on " + sku)
        current_policies = offer.get("listingPolicies") or {}
        if any(current_policies.get(k) not in (None, policies[k]) for k in POLICY_KEYS):
            raise DraftError("Different existing policies require human review for " + sku)
        if offer.get("merchantLocationKey") not in (None, location):
            raise DraftError("Different dispatch location on " + sku)
        ready.append((row, sku, offer))

    for row, sku, offer in ready:
        if (all((offer.get("listingPolicies") or {}).get(k) == policies[k] for k in POLICY_KEYS)
            and offer.get("merchantLocationKey") == location):
            print("POLICIES ALREADY CONFIGURED:", sku)
            continue
        payload = {
            "sku": sku,
            "marketplaceId": "EBAY_GB",
            "format": "FIXED_PRICE",
            "categoryId": row["category_id"],
            "availableQuantity": 0,
            "listingDuration": offer.get("listingDuration") or "GTC",
            "listingDescription": row["description"],
            "pricingSummary": {"price": {"value": row["price_gbp"], "currency": "GBP"}},
            "listingPolicies": policies,
            "merchantLocationKey": location
        }
        api._request("PUT", "/offer/" + offer["offerId"], payload)
        checked = api.offer(offer["offerId"])
        if (checked.get("status") != "UNPUBLISHED" or checked.get("listing")
            or checked.get("availableQuantity") != 0
            or checked.get("merchantLocationKey") != location
            or any((checked.get("listingPolicies") or {}).get(k) != policies[k] for k in POLICY_KEYS)):
            raise DraftError("Unexpected state after policy setup for " + sku)
        print("CONFIGURED UNPUBLISHED OFFER:", sku, "(no stock quantity or live listing created)")
    print("DONE: All three offers have the reference business policies and dispatch location, still UNPUBLISHED and 0 quantity.")
    print("Before publication: genuine product photographs, correct pack contents and actual packed postage verification are required.")

if __name__ == "__main__":
    try:
        main()
    except (DraftError, ValueError, KeyError, TypeError, OSError) as exc:
        print("BULK POLICY SETUP STOPPED:", exc, file=sys.stderr)
        sys.exit(1)
