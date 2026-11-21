"""Publish the existing stocked 100-piece disposable shower drain hair-catcher offer.

Fix the one documented eBay validation issue (missing Brand) without creating an
offer or changing price, category, shipping policies, product photos, or quantity.
Idempotent; only operates on this exact SKU and category.
"""
import json
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from ebay_client import Inventory, DraftError, get_token, ApiError

SKU = "DRAFT-HOME-DRAINCATCH100"
CATEGORY = "260554"
PRICE = "7.99"
EXPECTED_TITLE_START = "100 Disposable Shower Drain Hair Catcher"
REQUIRED_QTY = 1

def main():
    token = get_token()
    api = Inventory(token)
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
    current_aspect = aspects.get("Brand")
    current_brand = product.get("brand")
    if current_aspect not in (None, [], [""], ["Unbranded"]):
        raise DraftError("Existing non-generic Brand requires exact product verification")
    if current_brand not in (None, "", "Unbranded"):
        raise DraftError("Existing product brand differs from staged generic item")
    # eBay's Product.brand field is distinct from product.aspects.Brand.
    # Preserve both and let the marketplace validate its values.
    aspects["Brand"] = ["Unbranded"]
    # Generic product has no manufacturer part number; the recognised UK
    # unavailable identifier text is preferable to inventing an MPN.
    if aspects.get("MPN") not in (None, [], [""], ["Does not apply"]):
        raise DraftError("A different MPN needs verification")
    if product.get("mpn") not in (None, "", "Does not apply"):
        raise DraftError("Existing manufacturer MPN differs; refusing modification")
    aspects["MPN"] = ["Does not apply"]
    product["aspects"] = aspects
    product["brand"] = "Unbranded"
    product["mpn"] = "Does not apply"
    payload = {
        "product": product,
        "condition": "NEW",
        "availability": item["availability"],
    }
    for key in ("conditionDescription", "packageWeightAndSize"):
        if key in item:
            payload[key] = item[key]
    api.create_item(SKU, payload)
    saved = api.item(SKU)
    saved_prod = saved.get("product") or {}
    if (saved_prod.get("brand") != "Unbranded" or
        saved_prod.get("mpn") != "Does not apply" or
        (saved_prod.get("aspects") or {}).get("Brand") != ["Unbranded"] or
        (saved_prod.get("aspects") or {}).get("MPN") != ["Does not apply"]):
        raise DraftError("Required brand metadata did not save")
    if ((saved_prod.get("imageUrls") != photos) or
        (saved.get("availability") or {}).get("shipToLocationAvailability", {}).get("quantity") != REQUIRED_QTY):
        raise DraftError("Images or quantity changed unexpectedly")
    print("BRAND AND UNAVAILABLE MPN SET IN PRODUCT AND ASPECTS", flush=True)

    # Capture eBay's specific validation message without exposing credentials.
    request = Request(
        "https://api.ebay.com/sell/inventory/v1/offer/" + offer["offerId"] + "/publish",
        data=None, method="POST",
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json",
                 "Content-Language": "en-GB",
                 "Accept": "application/json"}
    )
    try:
        with urlopen(request, timeout=25) as response:
            result = json.loads(response.read())
    except HTTPError as exc:
        try:
            data = json.loads(exc.read())
            details = [{"id": e.get("errorId"),
                        "message": e.get("message"),
                        "longMessage": e.get("longMessage"),
                        "parameters": e.get("parameters")} for e in data.get("errors", [])]
        except (ValueError, KeyError, TypeError):
            details = []
        print("PUBLISH REJECTED HTTP", exc.code, "DETAILS", json.dumps(details, ensure_ascii=False)[:3500], flush=True)
        return
    except URLError:
        raise DraftError("Could not reach eBay; check offer state before retry")
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
