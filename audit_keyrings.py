"""Read-only readiness audit for existing Amazon keyring eBay offer."""
import sys
from ebay_client import Inventory, get_token, DraftError
from seller_readiness import get
SKU="DRAFT-AMZ-RINGS-25MM-50"

def audit():
    token=get_token()
    api=Inventory(token)
    api.check_access()
    item=api.item(SKU)
    offers=api.offers(SKU)
    if not item or len(offers)!=1: raise DraftError("Missing or nonunique offer")
    offer=api.offer(offers[0]["offerId"])
    product=item.get("product",{})
    print("SKU:",SKU)
    print("Inventory title:",product.get("title"))
    print("Current images:",len(product.get("imageUrls") or []))
    print("Inventory quantity:",item.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity"))
    print("Offer status:",offer.get("status"))
    print("Offer quantity:",offer.get("availableQuantity"))
    print("Is live:",bool(offer.get("listing")))
    print("Category:",offer.get("categoryId"))
    print("Price GBP:",offer.get("pricingSummary",{}).get("price",{}).get("value"))
    print("Has merchantLocationKey:",bool(offer.get("merchantLocationKey")))
    print("Has listingDuration:",bool(offer.get("listingDuration")))
    print("Policy keys:",sorted(offer.get("listingPolicies",{}).keys()))
    headers={"Authorization":"Bearer "+token,"Accept":"application/json","Content-Language":"en-GB"}
    for name,path,key in [
        ("fulfilment","fulfillment_policy","fulfillmentPolicies"),
        ("payment","payment_policy","paymentPolicies"),
        ("returns","return_policy","returnPolicies")]:
        status,data=get("https://api.ebay.com/sell/account/v1/"+path+"?marketplace_id=EBAY_GB",headers)
        print(name,"policies response:",status)
        if status!=200:continue
        for p in data.get(key,[]):
            summary={"id":p.get({"fulfilment":"fulfillmentPolicyId","payment":"paymentPolicyId","returns":"returnPolicyId"}[name]),"name":p.get("name")}
            if name=="fulfilment":
                summary["options"]=[{"type":x.get("optionType"),"services":[{"code":z.get("shippingServiceCode"),"free":z.get("freeShipping"),"cost":z.get("shippingCost",{}).get("value")} for z in x.get("shippingServices",[])]} for x in p.get("shippingOptions",[])]
            print(name,"policy:",summary)

if __name__=="__main__":
    try:audit()
    except (DraftError, ValueError, OSError) as ex:
        print("READONLY AUDIT FAILED:",ex,file=sys.stderr)
        sys.exit(1)
