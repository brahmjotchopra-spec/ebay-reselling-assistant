"""Prepare the existing Amazon split-ring eBay offer without publishing it.

This updates listing copy in eBay Inventory API, preserving zero stock. Photos and
live publication remain blocked until real inventory and dispatch are confirmed.
"""
import sys
from ebay_client import DraftError, Inventory, get_token

SKU = "DRAFT-AMZ-RINGS-25MM-50"
TITLE = "50 x 25mm Silver Split Key Rings Metal Keyring Hoops Keychain Craft Rings"
DESCRIPTION = (
    "Pack of 50 silver-coloured metal split key rings, approximately 25mm in diameter. "
    "Suitable for keyrings, keychain making, jewellery findings and craft projects. "
    "You receive 50 round split rings only. Keys, tags, and other accessories are not included. "
    "New and unused. Actual stock will be checked, counted and packed before it is offered for sale."
)
ASPECTS = {
    "Type": ["Split Ring"],
    "Colour": ["Silver"],
    "Material": ["Metal"],
    "Size": ["25 mm"],
    "Brand": ["Unbranded"],
}

def prep():
    api = Inventory(get_token())
    api.check_access()
    item = api.item(SKU)
    offers = api.offers(SKU)
    if not item or len(offers) != 1:
        raise DraftError("Existing candidate item and unique offer required")
    offer = offers[0]
    if item.get("sku") != SKU or offer.get("sku") != SKU:
        raise DraftError("SKU mismatch")
    if offer.get("status") != "UNPUBLISHED" or offer.get("listing"):
        raise DraftError("Refusing to change a live or unknown offer")
    if offer.get("availableQuantity") != 0:
        raise DraftError("Offer quantity is not zero")
    if item.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity") != 0:
        raise DraftError("Inventory quantity is not zero")
    if offer.get("categoryId") != "150055":
        raise DraftError("Category mismatch")
    if offer.get("pricingSummary",{}).get("price",{}).get("value") != "5.79":
        raise DraftError("Offer price changed; refusing automatic edit")
    product = dict(item.get("product",{}))
    if product.get("imageUrls"):
        raise DraftError("Existing photos require manual review before changing inventory")
    if product.get("title") not in (
        "50 x 25mm Silver Stainless Steel Split Key Rings Craft Keyring Hoops", TITLE
    ):
        raise DraftError("Unexpected existing title")
    product.update({"title": TITLE,"description": DESCRIPTION,"aspects": ASPECTS})
    item_payload = {
        "product": product,
        "condition": item.get("condition","NEW"),
        "availability": {"shipToLocationAvailability":{"quantity":0}}
    }
    api.create_item(SKU,item_payload)
    refreshed = api.item(SKU)
    if refreshed.get("product",{}).get("title") != TITLE or refreshed.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity") != 0:
        raise DraftError("Inventory update not verified")
    print("Listing title, description and item specifics updated in eBay Inventory API")
    if offer.get("listingDescription") != DESCRIPTION:
        wanted_keys = (
            "sku","marketplaceId","format","categoryId","availableQuantity",
            "pricingSummary","listingPolicies","merchantLocationKey","listingDuration",
            "includeCatalogProductDetails","tax"
        )
        payload = {key:offer[key] for key in wanted_keys if key in offer}
        payload["listingDescription"] = DESCRIPTION
        api._request("PUT","/offer/"+offer["offerId"],payload)
    checked=api.offer(offer["offerId"])
    if checked.get("listingDescription")!=DESCRIPTION:
        raise DraftError("Offer description update not verified")
    if checked.get("status")!="UNPUBLISHED" or checked.get("availableQuantity")!=0 or checked.get("listing"):
        raise DraftError("Offer state changed unexpectedly")
    print("Existing eBay offer updated and verified as UNPUBLISHED with quantity 0")
    print("No buyer-facing live listing or supplier order created; needs real product photos and stock.")

if __name__=="__main__":
    try:
        prep()
    except (DraftError, OSError, ValueError, KeyError) as ex:
        print("PREP FAILED:",ex,file=sys.stderr)
        sys.exit(1)
