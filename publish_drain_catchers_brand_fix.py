"""Publish the existing stocked 100-piece disposable shower drain hair-catcher offer.

Fix the one documented eBay validation issue (missing Brand) without creating an
offer or changing price, category, shipping policies, product photos, or quantity.
Idempotent; only operates on this exact SKU and category.
"""
import json
import sys
from ebay_client import Inventory, DraftError, get_token, ApiError

SKU = "DRAFT-HOME-DRAINCATCH100"
CATEGORY = "260554"
PRICE = "7.99"
EXPECTED_TITLE_START = "100 Disposable Shower Drain Hair Catcher"
REQUIRED_QTY = 1

def main():
    api = Inventory(get_token())
    api.check_access()
    offers = api.offers(SKU)
    if len(offers) != 1:
        raise DraftError("Missing/ambiguous existing drain catcher offer")
    offer = api.offer(offers[0]["offerId"])
    if offer.get("sku") != SKU or offer.get("categoryId") != CATEGORY:
        raise DraftError("Wrong product identity/category")

    if offer.get("status") == "PUBLISHED":
        listing_id = (offer.get("listing") or {}).get("listingId")
        if not listing_id:
            raise DraftError("Already published but listing ID missing")
        print("ALREADY LIVE https://www.ebay.co.uk/itm/" + str(listing_id), flush=True)
        return
    if offer.get("status") != "UNPUBLISHED" or offer.get("listing"):
        raise DraftError("Unexpected offer state; refusing edit")

    price = (offer.get("pricingSummary") or {}).get("price") or {}
    if str(price.get("value")) != PRICE or price.get("currency") != "GBP":
        raise DraftError("Offer price differs from approved £7.99")
    if offer.get("availableQuantity") != REQUIRED_QTY:
        raise DraftError("Expected exactly one pack of owned stock in offer")

    item = api.item(SKU)
    if not item or item.get("condition") != "NEW":
        raise DraftError("Inventory missing or unexpected condition")
    product = dict(item.get("product") or {})
    if not (product.get("title") or "").startswith(EXPECTED_TITLE_START):
        raise DraftError("Product title mismatch")
    photos = product.get("imageUrls")
    if not isinstance(photos, list) or len(photos) != 1:
        raise DraftError("Expected exactly one existing product illustration")
    current_stock = (item.get("availability") or {}).get("shipToLocationAvailability") or {}
    if current_stock.get("quantity") != REQUIRED_QTY:
        raise DraftError("Inventory stock does not equal one ready-to-ship pack")
    policies = offer.get("listingPolicies") or {}
    if not all(policies.get(k) for k in
               ("paymentPolicyId", "returnPolicyId", "fulfillmentPolicyId")):
        raise DraftError("Incomplete seller policies")
    if not offer.get("merchantLocationKey"):
        raise DraftError("Seller dispatch location is missing")

    aspects = dict(product.get("aspects") or {})
    brand = aspects.get("Brand")
    if brand is None or brand == [] or brand == [""]:
        # Generic no-brand mesh stickers; don't invent a manufacturer's name.
        aspects["Brand"] = ["Unbranded"]
        product["aspects"] = aspects
        payload = {
            "product": product,
            "condition": "NEW",
            "availability": item["availability"],
        }
        for key in ("conditionDescription", "packageWeightAndSize"):
            if key in item: payload[key] = item[key]
        api.create_item(SKU, payload)
        saved = api.item(SKU)
        if ((saved.get("product") or {}).get("aspects") or {}).get("Brand") != ["Unbranded"]:
            raise DraftError("Brand attribute did not save")
        if ((saved.get("product") or {}).get("imageUrls") != photos or
            (saved.get("availability") or {}).get("shipToLocationAvailability", {}).get("quantity") != REQUIRED_QTY):
            raise DraftError("Images or quantity changed unexpectedly")
        print("MISSING BRAND FIXED: Unbranded (generic product)", flush=True)
    else:
        print("Existing brand already present; not overwriting", flush=True)

    try:
        result = api._request("POST", "/offer/" + offer["offerId"] + "/publish")
    except ApiError as exc:
        print("EBAY REJECTED PUBLICATION HTTP", exc.status,
              "ERROR IDS", ",".join(map(str, sorted(exc.ids))), flush=True)
        return
    listing_id = result.get("listingId")
    if not listing_id:
        raise DraftError("Publish response has no listingId; reconcile before retry")
    checked = api.offer(offer["offerId"])
    if (checked.get("status") != "PUBLISHED" or
        str((checked.get("listing") or {}).get("listingId")) != str(listing_id) or
        (checked.get("pricingSummary") or {}).get("price") != price or
        checked.get("availableQuantity") != REQUIRED_QTY):
        raise DraftError("eBay live status, price or stock could not be verified")
    print("PUBLISHED AND VERIFIED https://www.ebay.co.uk/itm/" + str(listing_id), flush=True)
    print("PRICE GBP", PRICE, "STOCK PACKS", REQUIRED_QTY,
          "EXISTING ILLUSTRATION UNCHANGED", flush=True)

if __name__ == "__main__":
    try:
        main()
    except (DraftError, ValueError, KeyError, TypeError, OSError) as exc:
        print("DRAIN CATCHER PUBLICATION STOPPED:", exc, file=sys.stderr)
        sys.exit(1)
