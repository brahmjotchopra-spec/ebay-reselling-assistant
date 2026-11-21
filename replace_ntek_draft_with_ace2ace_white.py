"""Replace the sole unpublished NTEK single-brush offer with ACE2ACE WHITE roller.

A user has chosen an exact brand/colour from Amazon screenshots. The £19.99
target is unverified net of postage and selling fees. The user has not
confirmed stock ownership or an authorised fulfilment agreement, so stock is
held at ZERO and no publication action is performed.

Changes exactly one pre-existing draft, never creates a duplicate offer.
"""
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-HOME-PETHAIRBRUSH-1"
CATEGORY="170626"
PRICE="19.99"
TITLE="ACE2ACE Reusable Pet Hair Remover Roller White Lint Brush Sofa Dog Cat Fur"
DESCRIPTION=(
    "One ACE2ACE reusable pet hair remover roller, white colour. Manual cleaning "
    "roller intended to help lift loose pet hair and lint from suitable fabric "
    "sofas, bedding, rugs, cushions and upholstery. Use gently and test on a "
    "small inconspicuous area of delicate fabrics first. The flip-open collection "
    "compartment allows collected hair to be removed. One roller only; pets, "
    "furniture and other accessories are not included. The listing image is a "
    "digitally created visual illustration, not an actual photograph of retail "
    "stock. Exact packaging and model must match the supplier item."
)
ROOT="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/"
PHOTO=ROOT+"ace2ace_white_roller_studio.jpg"
OLD_TITLE="NTEK Reusable Pet Hair Remover Lint Cleaning Brush Sofa Carpet Clothes"

def check_photo():
    try:
        with urlopen(Request(PHOTO,headers={"User-Agent":"Mozilla/5.0"}),timeout=25) as resp:
            data=resp.read()
            if (resp.status != 200 or len(data)<50000 or
                not data.startswith(bytes.fromhex("ffd8ff"))):
                raise DraftError("Approved illustration not available as valid JPEG")
    except (HTTPError,URLError,OSError) as exc:
        raise DraftError("Illustration not publicly hosted on GitHub") from None
    print("VERIFIED ILLUSTRATIVE MAIN PHOTO",len(data),"bytes",flush=True)

def main():
    check_photo()
    api=Inventory(get_token())
    api.check_access()
    offers=api.offers(SKU)
    if len(offers)!=1:
        raise DraftError("Expected exactly one previously staged NTEK draft to replace")
    offer=api.offer(offers[0]["offerId"])
    if (offer.get("sku")!=SKU or offer.get("status")!="UNPUBLISHED" or
        offer.get("listing") or offer.get("categoryId")!=CATEGORY or
        offer.get("availableQuantity")!=0):
        raise DraftError("Draft offer changed or is live; refuse replacement")

    original_price=(offer.get("pricingSummary") or {}).get("price") or {}
    if (original_price.get("currency")!="GBP" or
        str(original_price.get("value")) not in ("8.99",PRICE)):
        raise DraftError("Existing offer price differs from approved previous/target price")
    policies=offer.get("listingPolicies") or {}
    required=("paymentPolicyId","returnPolicyId","fulfillmentPolicyId")
    if not all(policies.get(k) for k in required):
        raise DraftError("Existing seller business policies missing")
    location=offer.get("merchantLocationKey")
    if not location:
        raise DraftError("Existing dispatch location missing")

    item=api.item(SKU)
    if not item or item.get("condition")!="NEW":
        raise DraftError("Inventory record missing or not new-condition")
    oldproduct=item.get("product") or {}
    if (oldproduct.get("title") not in (OLD_TITLE,TITLE) or
        oldproduct.get("brand") not in ("NTEK","ACE2ACE") or
        (oldproduct.get("imageUrls") or []) not in ([],[PHOTO])):
        raise DraftError("SKU linked to different inventory content; refuse overwrite")
    qty=(item.get("availability") or {}).get("shipToLocationAvailability",{}).get("quantity")
    if qty!=0:
        raise DraftError("Refusing to modify actual stock or publish a product not yet purchased")

    newproduct={
        "title":TITLE,
        "description":DESCRIPTION,
        "brand":"ACE2ACE",
        "mpn":"Does not apply",
        "aspects":{
            "Brand":["ACE2ACE"],
            "MPN":["Does not apply"],
            "Colour":["White"],
            "Type":["Pet Hair Remover Roller"],
            "Features":["Reusable"],
            "Number in Pack":["1"]
        },
        "imageUrls":[PHOTO]
    }
    payload={"product":newproduct,"condition":"NEW","availability":item["availability"]}
    for key in ("conditionDescription","packageWeightAndSize"):
        if key in item:payload[key]=item[key]
    if oldproduct!=newproduct:
        api.create_item(SKU,payload)
        print("UPDATED DRAFT ITEM TO ACE2ACE WHITE ROLLER",flush=True)

    offer_body={
        "sku":SKU,
        "marketplaceId":"EBAY_GB",
        "format":"FIXED_PRICE",
        "categoryId":CATEGORY,
        "availableQuantity":0,
        "listingDescription":DESCRIPTION,
        "pricingSummary":{"price":{"currency":"GBP","value":PRICE}},
        "listingPolicies":{k:policies[k] for k in required},
        "merchantLocationKey":location,
        "listingDuration":offer.get("listingDuration") or "GTC"
    }
    if str(original_price.get("value"))!=PRICE or offer.get("listingDescription")!=DESCRIPTION:
        api._request("PUT","/offer/"+offer["offerId"],offer_body)
        print("UPDATED PRE-EXISTING OFFER ID",offer["offerId"],flush=True)

    after=api.offer(offer["offerId"])
    stored=api.item(SKU)
    got_price=(after.get("pricingSummary") or {}).get("price") or {}
    if (after.get("status")!="UNPUBLISHED" or after.get("listing") or
        after.get("sku")!=SKU or
        after.get("availableQuantity")!=0 or
        got_price.get("currency")!="GBP" or
        str(got_price.get("value"))!=PRICE or
        stored.get("product",{}).get("title")!=TITLE or
        stored.get("product",{}).get("brand")!="ACE2ACE" or
        stored.get("product",{}).get("imageUrls")!=[PHOTO] or
        stored.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=0):
        raise DraftError("ACE2ACE offer price/images/stock not confirmed by eBay")

    print("SUCCESS ACE2ACE WHITE ROLLER DRAFT REPLACED AND VERIFIED",flush=True)
    print("OFFER ID",offer["offerId"],"PRICE GBP",PRICE,flush=True)
    print("STOCK ZERO UNPUBLISHED; NO LIVE LISTING",flush=True)
    print("BLOCKED ON INVENTORY CONFIRMATION AND SHIPPING MARGIN",flush=True)

if __name__=="__main__":
    try:main()
    except (DraftError,ValueError,TypeError,KeyError,OSError) as exc:
        print("ACE2ACE STAGING FAILED:",exc,file=sys.stderr)
        sys.exit(1)
