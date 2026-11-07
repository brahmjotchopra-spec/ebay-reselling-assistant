"""Prepare UK fixed-price drafts, with an offline preview as the default."""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from ebay_client import ACCESS_KEY, REFRESH_KEYS, DraftError, Inventory, get_token


PENNY = Decimal("0.01")
BUDGET = Decimal("50.00")
FLOOR = Decimal("3.50")
SKU_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,43}")
PRICE_PATTERN = re.compile(r"[0-9]{1,6}(?:\.[0-9]{1,2})?")


def amount(value, field):
    if not isinstance(value, str) or not PRICE_PATTERN.fullmatch(value):
        raise DraftError(f"{field} needs a nonnegative decimal string.")
    return Decimal(value)


def money(value):
    return value.quantize(PENNY, rounding=ROUND_HALF_UP)


def link(value):
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password


def unit_margin(price, review):
    costs = [amount(review.get(k), k) for k in ("wholesale_inc_vat", "delivery_inc_vat",
             "supplier_payment_fee", "reserve_gbp", "insertion_ex_vat", "per_order_ex_vat")]
    wholesale, delivery, payment, reserve, insertion, order = costs
    rate = amount(review.get("ebay_percent"), "ebay_percent")
    vat = amount(review.get("fee_vat_percent"), "fee_vat_percent")
    if wholesale <= 0 or rate <= 0 or rate > 100 or vat > 100:
        raise DraftError("Invalid wholesale price or fee rate.")
    landed = wholesale + delivery + payment
    fees = money((price * rate / 100 + order + insertion) * (1 + vat / 100))
    return landed, fees, money(price - landed - fees - reserve)


def review_item(row, today):
    if row.get("approved_for_unpublished_offer") is not True:
        return "no draft approval"
    review = row.get("commercial_review")
    if not isinstance(review, dict) or review.get("verified") is not True:
        return "supplier terms or demand unverified"
    if review.get("checked_on") != today:
        return "supplier check needs refreshing"
    stock = review.get("stock")
    if type(stock) is not int or stock < 1:
        return "no confirmed stock"
    if not (link(review.get("supplier_url")) and link(review.get("demand_url"))
            and isinstance(review.get("delivery_terms"), str) and review["delivery_terms"].strip()):
        return "supplier, delivery or demand evidence missing"
    price = amount(row.get("price_gbp"), "price_gbp")
    landed, _, margin = unit_margin(price, review)
    if landed > BUDGET:
        return "one unit exceeds the £50 budget"
    if margin < FLOOR:
        return "unit margin below £3.50"
    return None


def payloads(row):
    sku = "DRAFT-" + row["sku"]
    for name, maximum in (("title", 80), ("description", 4000), ("condition", 50)):
        value = row.get(name)
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise DraftError(f"Missing or invalid {name}.")
    category = row.get("category_id")
    if not isinstance(category, str) or not re.fullmatch(r"[1-9][0-9]*", category):
        raise DraftError("A UK leaf category ID is required.")
    product = {k: row[k] for k in ("title", "description")}
    aspects = row.get("aspects", {})
    if not isinstance(aspects, dict) or any(
        not isinstance(k, str) or not k.strip() or not isinstance(v, list) or not v or
        not all(isinstance(x, str) and x.strip() for x in v) for k, v in aspects.items()
    ):
        raise DraftError("Invalid item specifics.")
    if aspects:
        product["aspects"] = aspects
    images = row.get("image_urls", [])
    if not isinstance(images, list) or len(images) > 24 or not all(link(i) for i in images):
        raise DraftError("Invalid supplier image URLs.")
    if images:
        product["imageUrls"] = images
    if row.get("ean"):
        if not re.fullmatch(r"[0-9]{13}", row["ean"]):
            raise DraftError("Invalid EAN.")
        product["ean"] = [row["ean"]]
    inventory = {"product": product, "condition": row["condition"],
                 "availability": {"shipToLocationAvailability": {"quantity": 0}}}
    offer = {"sku": sku, "marketplaceId": "EBAY_GB", "format": "FIXED_PRICE",
             "categoryId": category, "availableQuantity": 0, "listingDescription": row["description"],
             "pricingSummary": {"price": {"currency": "GBP", "value": row["price_gbp"]}}}
    return inventory, offer


def matches(actual, wanted):
    if isinstance(wanted, dict):
        return isinstance(actual, dict) and all(matches(actual.get(k), v) for k, v in wanted.items())
    return actual == wanted


def verify_offer(current, wanted):
    if not isinstance(current, dict) or current.get("status") != "UNPUBLISHED" or current.get("listing"):
        raise DraftError("SKU is linked to a published or unrecognised offer.")
    expected = dict(wanted)
    expected.pop("pricingSummary")
    price = current.get("pricingSummary", {}).get("price", {})
    if not matches(current, expected) or price.get("currency") != "GBP" or (
        amount(price.get("value"), "remote price") != Decimal(wanted["pricingSummary"]["price"]["value"])
    ):
        raise DraftError("Existing offer differs from the approved draft.")
    if not isinstance(current.get("offerId"), str) or not current["offerId"]:
        raise DraftError("Missing offer ID.")
    return current["offerId"]


def ensure_draft(api, inventory, offer):
    sku = offer["sku"]
    offers = api.offers(sku)
    existing = api.item(sku)
    if existing is not None and (existing.get("sku") != sku or not matches(existing, inventory)):
        raise DraftError("Existing inventory differs. No changes made to it.")
    if offers:
        if len(offers) != 1 or existing is None:
            raise DraftError("SKU is already in use or has an incomplete offer.")
        return "already verified", verify_offer(offers[0], offer)
    # PUT replaces an inventory item, so it is used only for an absent, reserved SKU.
    # On a retry, a matching item left by a previous partial run is reused.
    if existing is None:
        api.create_item(sku, inventory)
    offer_id = api.create_offer(offer)
    verified_id = verify_offer(api.offer(offer_id), offer)
    if offer_id != verified_id:
        raise DraftError("Offer ID mismatch after creation.")
    return "created and verified", verified_id


CSV_HEADER = ["Action(SiteID=UK|Country=GB|Currency=GBP|Version=1193|CC=UTF-8)",
              "Custom label (SKU)", "Category ID", "Title", "UPC", "Price", "Quantity",
              "Item photo URL", "Condition ID", "Description", "Format"]


def write_csv(path, rows):
    # Prepare all rows before opening the file. Refuse to leave a stale export in use.
    records = []
    for row in rows:
        inventory, offer = payloads(row)
        if inventory["condition"] != "NEW":
            raise DraftError("This dropshipping CSV supports new stock only.")
        records.append(["Draft", offer["sku"], row["category_id"], row["title"], "",
                        row["price_gbp"], "", "|".join(row.get("image_urls", [])),
                        "NEW", row["description"], "FixedPrice"])
    with path.open("x", encoding="utf-8-sig", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["#INFO", "Version=0.0.2", "Template= eBay-draft-listings-template_GB"])
        writer.writerow(CSV_HEADER)
        writer.writerows(records)


def prepare(raw, today):
    if not isinstance(raw, list):
        raise DraftError("Listings must be a JSON array.")
    ready, held, seen = [], [], set()
    for n, row in enumerate(raw, 1):
        if not isinstance(row, dict):
            raise DraftError(f"Row {n} must be an object.")
        sku = row.get("sku")
        if not isinstance(sku, str) or not SKU_PATTERN.fullmatch(sku) or sku.upper() in seen:
            raise DraftError(f"Row {n} has an invalid or duplicate SKU.")
        seen.add(sku.upper())
        reason = review_item(row, today)
        if reason:
            held.append((n, reason))
        else:
            payloads(row)
            ready.append(row)
    cash = sum((unit_margin(Decimal(row["price_gbp"]), row["commercial_review"])[0] for row in ready),
               Decimal(0))
    if cash > BUDGET:
        raise DraftError("One fulfilment for each ready SKU would exceed the £50 budget.")
    return ready, held


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, help="Private listings file (default: listings.json)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-credentials", action="store_true")
    mode.add_argument("--create-unpublished", action="store_true")
    mode.add_argument("--seller-hub-csv", type=Path, metavar="NEW_FILE")
    args = parser.parse_args()
    try:
        if args.check_credentials:
            for key in (*REFRESH_KEYS, ACCESS_KEY):
                print(f"{key}: {'present' if os.environ.get(key, '').strip() else 'missing'}")
            Inventory(get_token()).check_access()
            print("Production seller Inventory read succeeded.")
            return 0
        if args.file:
            source = args.file.read_text(encoding="utf-8-sig")
        else:
            source = os.environ.get("EBAY_LISTINGS_JSON") or Path("listings.json").read_text(encoding="utf-8-sig")
        today = datetime.now(ZoneInfo("Europe/London")).date().isoformat()
        ready, held = prepare(json.loads(source), today)
        print(f"{len(ready)} eligible, {len(held)} held.")
        for n, reason in held:
            print(f"Row {n}: {reason}.")
        if args.seller_hub_csv:
            if not ready:
                raise DraftError("No eligible rows to export.")
            write_csv(args.seller_hub_csv, ready)
        elif args.create_unpublished and ready:
            api = Inventory(get_token())
            api.check_access()
            for n, row in enumerate(ready, 1):
                state, offer_id = ensure_draft(api, *payloads(row))
                receipt = "" if os.environ.get("GITHUB_ACTIONS") else f" (offer {offer_id})"
                print(f"Eligible row {n}: {state}{receipt}.")
        return 0
    except (DraftError, OSError, ValueError) as exc:
        print(f"Stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
