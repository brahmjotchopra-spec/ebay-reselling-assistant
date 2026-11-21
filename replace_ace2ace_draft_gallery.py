"""Replace the image gallery on the existing UNPUBLISHED ACE2ACE WHITE roller offer.

Use seller-provided product gallery screenshot crops hosted on GitHub, replacing
the AI illustration. Keep the £19.99 provisional price and zero available
quantity. Never create new offers or publish any listing.
"""
import sys
import time
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-HOME-PETHAIRBRUSH-1"
OFFER_ID="367587272011"
PRICE="19.99"
CATEGORY="170626"
TITLE="ACE2ACE Reusable Pet Hair Remover Roller White Lint Brush Sofa Dog Cat Fur"
ROOT="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/"
OLD=[ROOT+"ace2ace_white_roller_studio.jpg"]
NEW=[ROOT+"ace2ace_gallery_product.jpg",
     ROOT+"ace2ace_gallery_in_use.jpg",
     ROOT+"ace2ace_gallery_cleaning.jpg",
     ROOT+"ace2ace_gallery_surfaces.jpg"]
DESCRIPTION=(
    "One ACE2ACE reusable pet hair remover roller in white. Manual cleaning "
    "roller intended to help lift loose hair and lint from compatible sofas, "
    "pet bedding, rugs, cushions, clothing and upholstery. Use gently and test "
    "on an inconspicuous area of delicate fabrics first. The flip-open "
    "collection compartment allows collected hair to be removed. "
    "One white roller only; furniture, pets and accessories shown are not "
    "included. These product-gallery reference pictures were supplied by "
    "the seller; they are not photographs of the seller's physical stock. "
    "Exact model and packaging must be checked against the supplier item."
)

def validate_photos():
    for url in NEW:
        found=False
        for attempt in range(9):
            try:
                request=Request(url,headers={"User-Agent":"Mozilla/5.0"})
                with urlopen(request,timeout=18) as resp:
                    data=resp.read()
                    if (resp.status==200 and len(data)>40000 and
                        data.startswith(bytes.fromhex("ffd8ff"))):
                        found=True
                        print("PHOTO ACCESSIBLE",url.rsplit("/",1)[-1],len(data),flush=True)
                        break
            except (HTTPError,URLError,OSError):
                pass
            time.sleep(2)
        if not found:
            raise DraftError("Image not publicly accessible: "+url.rsplit("/",1)[-1])

def main():
    validate_photos()
    api=Inventory(get_token())
    api.check_access()
    offers=api.offers(SKU)
    if len(offers)!=1 or offers[0].get("offerId")!=OFFER_ID:
        raise DraftError("Expected a single known ACE2ACE draft")
    offer=api.offer(OFFER_ID)
    if (offer.get("sku")!=SKU or offer.get("status")!="UNPUBLISHED" or
        offer.get("listing") or offer.get("availableQuantity")!=0 or
        offer.get("categoryId")!=CATEGORY):
        raise DraftError("Draft changed, already published or stocked; not changing")
    price=(offer.get("pricingSummary") or {}).get("price") or {}
    if price.get("currency")!="GBP" or str(price.get("value"))!=PRICE:
        raise DraftError("Draft price differs from approved £19.99")
    policies=offer.get("listingPolicies") or {}
    required=("paymentPolicyId","returnPolicyId","fulfillmentPolicyId")
    if not all(policies.get(k) for k in required):
        raise DraftError("Missing seller policies")
    if not offer.get("merchantLocationKey"):
        raise DraftError("Missing seller dispatch location")
    item=api.item(SKU)
    if not item or item.get("condition")!="NEW":
        raise DraftError("Wrong condition or missing inventory")
    product=dict(item.get("product") or {})
    if product.get("title")!=TITLE or product.get("brand")!="ACE2ACE":
        raise DraftError("Wrong existing model or brand")
    if product.get("imageUrls") not in (OLD,NEW):
        raise DraftError("Photo list differs from original/approved gallery")
    if (item.get("availability") or {}).get("shipToLocationAvailability",{}).get("quantity")!=0:
        raise DraftError("Unexpected stock; refusing change")
    if product.get("imageUrls")!=NEW or product.get("description")!=DESCRIPTION:
        product["imageUrls"]=NEW
        product["description"]=DESCRIPTION
        payload={"product":product,"condition":"NEW","availability":item["availability"]}
        for key in ("conditionDescription","packageWeightAndSize"):
            if key in item:payload[key]=item[key]
        api.create_item(SKU,payload)
    if offer.get("listingDescription")!=DESCRIPTION:
        body={
            "sku":SKU,"marketplaceId":"EBAY_GB","format":"FIXED_PRICE",
            "categoryId":CATEGORY,"availableQuantity":0,
            "listingDuration":offer.get("listingDuration") or "GTC",
            "listingDescription":DESCRIPTION,
            "pricingSummary":{"price":{"value":PRICE,"currency":"GBP"}},
            "listingPolicies":{k:policies[k] for k in required},
            "merchantLocationKey":offer["merchantLocationKey"],
        }
        api._request("PUT","/offer/"+OFFER_ID,body)
    saved=api.item(SKU)
    checked=api.offer(OFFER_ID)
    savedproduct=saved.get("product") or {}
    if (savedproduct.get("imageUrls")!=NEW or
        savedproduct.get("description")!=DESCRIPTION or
        savedproduct.get("title")!=TITLE or
        saved.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=0 or
        checked.get("status")!="UNPUBLISHED" or checked.get("listing") or
        checked.get("availableQuantity")!=0 or
        checked.get("listingDescription")!=DESCRIPTION or
        checked.get("pricingSummary",{}).get("price")!=price):
        raise DraftError("eBay image/description/zero-stock readback failed")
    print("SUCCESS: FOUR SELLER-PROVIDED ACE2ACE GALLERY PHOTOS VERIFIED IN EBAY DRAFT",flush=True)
    print("OFFER",OFFER_ID,"PRICE GBP",PRICE,"UNPUBLISHED ZERO AVAILABLE",flush=True)
    print("IMAGES",len(NEW),flush=True)
    for u in NEW:print("PHOTO",u,flush=True)

if __name__=="__main__":
    try:main()
    except (DraftError,ValueError,TypeError,KeyError,OSError) as exc:
        print("ACE2ACE GALLERY REPLACEMENT FAILED:",exc,file=sys.stderr)
        sys.exit(1)
