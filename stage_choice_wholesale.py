"""Stage the four Choice Wholesale research candidates as zero-stock UNPUBLISHED eBay offers.

No supplier order, live listing, inventory stock or buyer fulfilment is created.
Commercial claims remain explicitly unverified; never attempt to publish.
"""
import json
import sys
from pathlib import Path

from ebay_bot import payloads, ensure_draft
from ebay_client import DraftError, Inventory, get_token

SOURCE = Path("research/choice-wholesale-listing-batch-2026-11-22.json")
EXPECTED = {
    "DRAFT-CHW-JANRAX13-BLACK2": ("5.89", "122951"),
    "DRAFT-CHW-JANRAX13-GREEN2": ("5.89", "122951"),
    "DRAFT-CHW-JANRAX8-BLUE2": ("5.49", "122951"),
    "DRAFT-CHW-JANRAX-PENCLIP6": ("6.99", "102953"),
}


def prepare():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    if (data.get("publish_permitted") is not False
        or data.get("stock_confirmed") is not False
        or data.get("image_rights_confirmed") is not False
        or data.get("source_delivery_to_user_confirmed") is not False):
        raise DraftError("Research safety holds were changed: refuse staging")
    raw = data.get("products")
    if not isinstance(raw, list) or len(raw) != 4:
        raise DraftError("Four expected products required")
    if {x.get("sku") for x in raw} != set(EXPECTED):
        raise DraftError("Product SKUs have changed; refusing staging")

    prepared = []
    for x in raw:
        full_sku = x["sku"]
        if (x.get("price_gbp"), x.get("category_id")) != EXPECTED[full_sku]:
            raise DraftError("Price or category changed for " + full_sku)
        row = {
            "sku": full_sku.removeprefix("DRAFT-"),
            "title": x["title"],
            "description": x["description"],
            "category_id": x["category_id"],
            "price_gbp": x["price_gbp"],
            "condition": "NEW",
            "aspects": {"Brand": [x["brand"]]},
            "image_urls": [],
        }
        inventory, offer = payloads(row)
        if (offer["sku"] != full_sku
            or offer["availableQuantity"] != 0
            or inventory["availability"]["shipToLocationAvailability"]["quantity"] != 0
            or inventory["product"].get("imageUrls")):
            raise DraftError("Not a safe zero-stock staging record")
        prepared.append((full_sku, inventory, offer))
    return prepared


def run():
    records = prepare()
    api = Inventory(get_token())
    api.check_access()
    print("Authentication verified; starting NON-LIVE staging", flush=True)

    # Preflight every SKU before writing any new items/offers.
    for sku, inventory, offer in records:
        old_item = api.item(sku)
        old_offers = api.offers(sku)
        if old_item and (
            old_item.get("sku") != sku
            or old_item.get("availability", {}).get("shipToLocationAvailability", {}).get("quantity") != 0
            or old_item.get("condition") != "NEW"
            or old_item.get("product", {}).get("title") != inventory["product"]["title"]
        ):
            raise DraftError("Existing inventory conflict for " + sku)
        if old_offers:
            if len(old_offers) != 1 or not old_item:
                raise DraftError("Offer count or inventory conflict for " + sku)
            current = api.offer(old_offers[0]["offerId"])
            if current.get("status") != "UNPUBLISHED" or current.get("listing"):
                raise DraftError("Existing published or unexpected offer for " + sku)

    for sku, inventory, offer in records:
        status, offer_id = ensure_draft(api, inventory, offer)
        verify = api.offer(offer_id)
        item = api.item(sku)
        if (
            verify.get("status") != "UNPUBLISHED"
            or verify.get("listing")
            or verify.get("availableQuantity") != 0
            or item.get("availability", {}).get("shipToLocationAvailability", {}).get("quantity") != 0
        ):
            raise DraftError("Unpublished stock-zero verification failed for " + sku)
        print(f"CONFIRMED UNPUBLISHED {sku} GBP {offer['pricingSummary']['price']['value']} OFFER_ID {offer_id} ({status})", flush=True)
    print("Four unpublished offers verified; zero live listings, no purchases", flush=True)


if __name__ == "__main__":
    try:
        run()
    except (DraftError, KeyError, TypeError, OSError, ValueError) as e:
        print("CHOICE WHOLESALE STAGING STOPPED:", str(e), file=sys.stderr)
        sys.exit(1)
