"""Publish exactly the existing ACE2ACE white pet-hair roller eBay offer.

The user has explicitly confirmed possession of stock and requested publication.
Offer only ONE unit (conservative default). Never create an offer or duplicate
listing, change price/policies/gallery, or modify unrelated inventory.
"""
import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-HOME-PETHAIRBRUSH-1"
OFFER_ID="367587272011"
PRICE="19.99"
CATEGORY="170626"
TITLE="ACE2ACE Reusable Pet Hair Remover Roller White Lint Brush Sofa Dog Cat Fur"
ROOT="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/"
PHOTOS=[
    ROOT+"ace2ace_gallery_product.jpg",
    ROOT+"ace2ace_gallery_in_use.jpg",
    ROOT+"ace2ace_gallery_cleaning.jpg",
    ROOT+"ace2ace_gallery_surfaces.jpg",
]
POLICIES=("paymentPolicyId","returnPolicyId","fulfillmentPolicyId")
QTY=1

def safe_publish(token):
    req=Request(
        "https://api.ebay.com/sell/inventory/v1/offer/"+OFFER_ID+"/publish",
        method="POST",
        headers={"Authorization":"Bearer "+token,
                 "Accept":"application/json",
                 "Content-Type":"application/json",
                 "Content-Language":"en-GB"}
    )
    try:
        with urlopen(req,timeout=28) as response:
            return json.loads(response.read() or b"{}")
    except HTTPError as exc:
        try:
            payload=json.loads(exc.read().decode("utf-8","replace"))
            details=[{
              "errorId":e.get("errorId"),
              "message":e.get("message"),
              "parameters":e.get("parameters")
            } for e in payload.get("errors",[]) if isinstance(e,dict)]
        except (ValueError,TypeError,UnicodeError):
            details=[]
        raise DraftError("eBay REJECTED publication HTTP "+str(exc.code)+" "+json.dumps(details,ensure_ascii=False)[:3500]) from None

def main():
    token=get_token()
    api=Inventory(token)
    api.check_access()
    offers=api.offers(SKU)
    if len(offers)!=1 or offers[0].get("offerId")!=OFFER_ID:
        raise DraftError("Known ACE2ACE single-unit offer missing or ambiguous: no duplicates")
    offer=api.offer(OFFER_ID)
    if offer.get("sku")!=SKU or offer.get("categoryId")!=CATEGORY:
        raise DraftError("SKU or product category does not match")
    price=(offer.get("pricingSummary") or {}).get("price") or {}
    if price.get("currency")!="GBP" or str(price.get("value"))!=PRICE:
        raise DraftError("Price differs from user-approved GBP 19.99")
    if not offer.get("merchantLocationKey"):
        raise DraftError("Seller dispatch location missing")
    policies=offer.get("listingPolicies") or {}
    if not all(policies.get(k) for k in POLICIES):
        raise DraftError("Seller return/payment/postage policies missing")
    item=api.item(SKU)
    if not item or item.get("condition")!="NEW":
        raise DraftError("Seller inventory item not new")
    product=item.get("product") or {}
    if (product.get("title")!=TITLE or product.get("brand")!="ACE2ACE"
            or product.get("imageUrls")!=PHOTOS):
        raise DraftError("Expected precise ACE2ACE model/title and four seller-selected images")
    if "white" not in TITLE.lower() or (product.get("aspects") or {}).get("Colour")!=["White"]:
        raise DraftError("Wrong variant; expected white")
    saved_desc=product.get("description")
    if not isinstance(saved_desc,str) or not saved_desc:
        raise DraftError("Inventory product description missing")
    if offer.get("listingDescription")!=saved_desc:
        raise DraftError("Offer description and images have not been reconciled")
    avail=item.get("availability") or {}
    stock=(avail.get("shipToLocationAvailability") or {}).get("quantity")
    if type(stock)!=int or stock not in (0,QTY):
        raise DraftError("Unknown inventory quantity; will not overwrite")
    already=offer.get("status")=="PUBLISHED"
    if already:
        listing=(offer.get("listing") or {}).get("listingId")
        if not listing or stock!=QTY or offer.get("availableQuantity")!=QTY:
            raise DraftError("Previously published listing has unexpected stock; check manually")
        print("ALREADY PUBLISHED VERIFIED https://www.ebay.co.uk/itm/"+str(listing),flush=True)
        return
    if offer.get("status")!="UNPUBLISHED" or offer.get("listing"):
        raise DraftError("Unknown offer status; refusing modification")
    if offer.get("availableQuantity") not in (0,QTY):
        raise DraftError("Existing offered quantity is unexpected")
    if stock==0:
        update_avail=dict(avail)
        ship=dict(avail.get("shipToLocationAvailability") or {})
        ship["quantity"]=QTY
        update_avail["shipToLocationAvailability"]=ship
        item_body={
            "product":product,
            "condition":"NEW",
            "availability":update_avail
        }
        for key in ("conditionDescription","packageWeightAndSize"):
            if key in item:item_body[key]=item[key]
        api.create_item(SKU,item_body)
        print("SET CONSERVATIVE OWNED INVENTORY QUANTITY",QTY,flush=True)

    if offer.get("availableQuantity")!=QTY:
        offer_body={
            "sku":SKU,
            "marketplaceId":"EBAY_GB",
            "format":"FIXED_PRICE",
            "categoryId":CATEGORY,
            "availableQuantity":QTY,
            "listingDescription":saved_desc,
            "pricingSummary":{"price":{"value":PRICE,"currency":"GBP"}},
            "listingPolicies":{k:policies[k] for k in POLICIES},
            "merchantLocationKey":offer["merchantLocationKey"],
            "listingDuration":offer.get("listingDuration") or "GTC",
        }
        api._request("PUT","/offer/"+OFFER_ID,offer_body)
        print("SET OFFER AVAILABLE QUANTITY",QTY,flush=True)

    item_check=api.item(SKU)
    offer_check=api.offer(OFFER_ID)
    if (item_check.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=QTY or
        item_check.get("product",{}).get("imageUrls")!=PHOTOS or
        offer_check.get("availableQuantity")!=QTY or
        offer_check.get("status")!="UNPUBLISHED" or
        offer_check.get("pricingSummary",{}).get("price")!=price):
        raise DraftError("Stock/gallery/offer pre-publication verification failed")

    published=safe_publish(token)
    lid=published.get("listingId")
    if not lid:
        raise DraftError("Publish API returned no listing ID; reconcile before retry")
    final_offer=api.offer(OFFER_ID)
    final_item=api.item(SKU)
    if (final_offer.get("status")!="PUBLISHED" or
        str((final_offer.get("listing") or {}).get("listingId"))!=str(lid) or
        final_offer.get("availableQuantity")!=QTY or
        final_offer.get("pricingSummary",{}).get("price")!=price or
        final_item.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=QTY or
        final_item.get("product",{}).get("imageUrls")!=PHOTOS):
        raise DraftError("eBay publication or listing details could not be verified")
    print("SUCCESS: LIVE EBAY ACE2ACE WHITE PET HAIR ROLLER",flush=True)
    print("LISTING https://www.ebay.co.uk/itm/"+str(lid),flush=True)
    print("PRICE GBP",PRICE,"QUANTITY",QTY,"PHOTOS",len(PHOTOS),flush=True)
    print("OFFER",OFFER_ID,flush=True)

if __name__=="__main__":
    try:
        main()
    except (DraftError,ValueError,KeyError,TypeError,OSError) as exc:
        print("ACE2ACE PUBLISH STOPPED:",exc,file=sys.stderr)
        sys.exit(1)
