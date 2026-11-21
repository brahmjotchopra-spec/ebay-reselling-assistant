"""Publish one owned-stock 100-pack of 6 mm silver-tone open jump rings.

Only the specified existing eBay offer is eligible. Idempotent: do not create
another offer or duplicate an already-live listing. The artwork is an original
illustration, not a photograph of stock, so label it as such in the description.
"""
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from ebay_client import Inventory, DraftError, get_token

SKU = "DRAFT-BULK-JUMP-6MM-100"
PHOTO = "https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/bulk-6mm-jump-rings.jpg"
CATEGORY = "150055"
PRICE = "3.99"
TITLE = "100 x 6mm Silver Tone Open Jump Rings Metal Jewellery Making Craft Findings"
DESCRIPTION = (
    "Pack of 100 silver-tone metal open jump rings, nominal 6mm outer diameter. "
    "Suitable for jewellery making, bracelets, necklace repairs, charm making and craft projects. "
    "You receive 100 loose open jump rings only. No finished jewellery, tools, chains or charms included. "
    "The main image is a digitally drawn illustration of this product type, not a photograph of the physical stock. "
    "Exact colour tone and finish may vary slightly."
)
QUANTITY = 1  # Limit exposure to one prepared/packable 100-ring lot.

def confirm_image():
    for _ in range(5):
        try:
            request = Request(PHOTO, method="GET", headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=12) as response:
                first = response.read(3)
                if (response.status == 200 and
                    response.headers.get("Content-Type", "").startswith("image/jpeg") and
                    first == bytes.fromhex("ffd8ff")):
                    return
        except (OSError, URLError, HTTPError):
            pass
        time.sleep(2)
    raise DraftError("Listing image is not publicly reachable as a JPEG")

def main():
    confirm_image()
    api = Inventory(get_token())
    api.check_access()
    offers = api.offers(SKU)
    if len(offers) != 1:
        raise DraftError("Expected exactly one existing 6 mm jump-ring offer")
    offer = api.offer(offers[0]["offerId"])
    if offer.get("sku") != SKU:
        raise DraftError("Offer SKU does not match")
    if offer.get("status") == "PUBLISHED":
        listing_id = (offer.get("listing") or {}).get("listingId")
        if not listing_id:
            raise DraftError("Offer published but listing ID unavailable")
        print("ALREADY LIVE (no duplicate created): https://www.ebay.co.uk/itm/" + str(listing_id))
        return
    if offer.get("status") != "UNPUBLISHED" or offer.get("listing"):
        raise DraftError("Unexpected offer state; refusing modification")
    if offer.get("categoryId") != CATEGORY:
        raise DraftError("Wrong category")
    price = (offer.get("pricingSummary") or {}).get("price") or {}
    if str(price.get("value")) != PRICE or price.get("currency") != "GBP":
        raise DraftError("Unapproved price change or currency mismatch")

    existing = api.item(SKU)
    if not existing or existing.get("sku") != SKU:
        raise DraftError("Existing inventory missing")
    if existing.get("condition") != "NEW":
        raise DraftError("Only new-condition stock may be published")
    if existing.get("availability", {}).get("shipToLocationAvailability", {}).get("quantity") not in (0, 1):
        raise DraftError("Unexpected inventory quantity")
    if offer.get("availableQuantity") not in (0, 1):
        raise DraftError("Unexpected offer quantity")
    policy = offer.get("listingPolicies") or {}
    if not all(policy.get(key) for key in ("paymentPolicyId", "returnPolicyId", "fulfillmentPolicyId")):
        raise DraftError("Incomplete payment, return or shipping policies")
    if not offer.get("merchantLocationKey"):
        raise DraftError("No eBay merchant dispatch location")
    oldtitle = (existing.get("product") or {}).get("title") or ""
    if not oldtitle.startswith("100 x 6mm Silver Tone"):
        raise DraftError("Existing item title does not match target jump rings")

    product = dict(existing.get("product") or {})
    product["title"] = TITLE
    product["description"] = DESCRIPTION
    product["imageUrls"] = [PHOTO]
    aspects = dict(product.get("aspects") or {})
    aspects["Type"] = ["Open Jump Ring"]
    aspects["Colour"] = ["Silver"]
    aspects["Size"] = ["6 mm"]
    aspects["Material"] = ["Metal"]
    product["aspects"] = aspects
    invbody = {
        "product": product,
        "condition": "NEW",
        "availability": {"shipToLocationAvailability": {"quantity": QUANTITY}},
    }
    api.create_item(SKU, invbody)
    verified_item = api.item(SKU)
    if (verified_item.get("product", {}).get("imageUrls") != [PHOTO] or
        verified_item.get("availability", {}).get("shipToLocationAvailability", {}).get("quantity") != QUANTITY):
        raise DraftError("Inventory/photo change failed verification")

    body = {
        "sku": SKU,
        "marketplaceId": "EBAY_GB",
        "format": "FIXED_PRICE",
        "categoryId": CATEGORY,
        "availableQuantity": QUANTITY,
        "listingDuration": offer.get("listingDuration") or "GTC",
        "listingDescription": DESCRIPTION,
        "pricingSummary": {"price": {"value": PRICE, "currency": "GBP"}},
        "listingPolicies": policy,
        "merchantLocationKey": offer["merchantLocationKey"],
    }
    api._request("PUT", "/offer/" + offer["offerId"], body)
    refreshed = api.offer(offer["offerId"])
    if (refreshed.get("status") != "UNPUBLISHED" or
        refreshed.get("availableQuantity") != QUANTITY or
        (refreshed.get("pricingSummary") or {}).get("price", {}).get("value") != PRICE):
        raise DraftError("Offer state unexpectedly changed before publication")
    result = api._request("POST", "/offer/" + offer["offerId"] + "/publish")
    listing_id = result.get("listingId")
    if not listing_id:
        raise DraftError("eBay publish response missing listing ID; inspect state before retry")
    after = api.offer(offer["offerId"])
    if (after.get("status") != "PUBLISHED" or
        str((after.get("listing") or {}).get("listingId")) != str(listing_id)):
        raise DraftError("eBay publish succeeded but read-back verification disagrees")
    print("PUBLISHED 100 x 6mm OPEN JUMP RINGS")
    print("LISTING URL https://www.ebay.co.uk/itm/" + str(listing_id))
    print("Price GBP " + PRICE + ", quantity " + str(QUANTITY))

if __name__ == "__main__":
    try:
        main()
    except (DraftError, ValueError, OSError, KeyError, TypeError) as exc:
        print("PUBLISH ATTEMPT STOPPED: " + str(exc), file=sys.stderr)
        sys.exit(1)
