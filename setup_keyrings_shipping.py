"""Configure free Royal Mail 2nd Class UK business policy for stocked keyrings.

Set policy and existing enabled home dispatch location on the *unpublished* offer.
Never upload artificial pictures, increase quantity, or publish.
"""
import json
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from ebay_client import Inventory, get_token, DraftError

SKU = "DRAFT-AMZ-RINGS-25MM-50"
POLICY_NAME = "Keyring Multipacks - Royal Mail 2nd Class Free UK"
LOCATION_KEY = "home_dispatch_uk"
BASE = "https://api.ebay.com/sell/account/v1/fulfillment_policy"
PAYMENT_ID = "254751987026"
RETURNS_ID = "254752096026"

def request(method,url,token,payload=None):
    headers={"Authorization":"Bearer "+token,"Content-Language":"en-GB","Accept":"application/json","Content-Type":"application/json"}
    data=None if payload is None else json.dumps(payload).encode()
    try:
        with urlopen(Request(url,method=method,headers=headers,data=data),timeout=25) as r:
            b=r.read()
            return json.loads(b) if b.strip() else {}
    except HTTPError as e:
        try: ids=[x.get("errorId") for x in json.loads(e.read()).get("errors",[]) if isinstance(x,dict)]
        except (ValueError,TypeError): ids=[]
        raise DraftError("eBay "+method+" policy HTTP "+str(e.code)+" error codes "+str(ids)) from None
    except URLError:
        raise DraftError("Cannot contact eBay") from None

def main():
    token=get_token()
    inv=Inventory(token)
    inv.check_access()
    item=inv.item(SKU)
    offers=inv.offers(SKU)
    if not item or len(offers)!=1:raise DraftError("Expected existing single keyring offer")
    offer=inv.offer(offers[0]["offerId"])
    if offer.get("sku")!=SKU or offer.get("status")!="UNPUBLISHED" or offer.get("listing"):
        raise DraftError("Refusing offer not in expected unpublished state")
    if offer.get("availableQuantity")!=0 or item.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=0:
        raise DraftError("Refusing stock-positive offer before photos and weight confirmed")
    if offer.get("categoryId")!="150055" or offer.get("pricingSummary",{}).get("price",{}).get("value")!="5.79":
        raise DraftError("Listing category/price mismatch")
    locations=inv._request("GET","/location?limit=100").get("locations",[])
    matched=[x for x in locations if x.get("merchantLocationKey")==LOCATION_KEY]
    if len(matched)!=1 or matched[0].get("merchantLocationStatus")!="ENABLED":
        raise DraftError("Expected enabled seller dispatch location not found")
    existing=request("GET",BASE+"?marketplace_id=EBAY_GB",token)
    matches=[x for x in existing.get("fulfillmentPolicies",[]) if x.get("name")==POLICY_NAME]
    if len(matches)>1:raise DraftError("Duplicate named shipping policies; reconcile manually")
    if matches:
        p=matches[0]
        services=[s for o in p.get("shippingOptions",[]) if o.get("optionType")=="DOMESTIC" for s in o.get("shippingServices",[])]
        if not any(s.get("shippingServiceCode")=="UK_RoyalMailSecondClassStandard" and s.get("freeShipping") is True for s in services):
            raise DraftError("Named policy exists but terms mismatch")
        policy_id=p["fulfillmentPolicyId"]
        print("Reusing matching Royal Mail 2nd Class free-shipping policy")
    else:
        payload={
            "name":POLICY_NAME,
            "marketplaceId":"EBAY_GB",
            "categoryTypes":[{"name":"ALL_EXCLUDING_MOTORS_VEHICLES"}],
            "handlingTime":{"value":2,"unit":"DAY"},
            "shippingOptions":[{
                "optionType":"DOMESTIC","costType":"FLAT_RATE",
                "shippingServices":[{
                    "shippingCarrierCode":"RoyalMail",
                    "shippingServiceCode":"UK_RoyalMailSecondClassStandard",
                    "freeShipping":True,
                    "shippingCost":{"value":"0.00","currency":"GBP"}
                }]
            }]
        }
        created=request("POST",BASE,token,payload)
        policy_id=created.get("fulfillmentPolicyId")
        if not policy_id:raise DraftError("No shipping policy id returned")
        print("Created dedicated free Royal Mail 2nd Class UK policy")
    policies={"paymentPolicyId":PAYMENT_ID,"returnPolicyId":RETURNS_ID,"fulfillmentPolicyId":policy_id}
    if all(offer.get("listingPolicies",{}).get(k)==v for k,v in policies.items()) and offer.get("merchantLocationKey")==LOCATION_KEY:
        print("Offer already has matching policies and dispatch origin")
        return
    payload={
        "sku":SKU,
        "marketplaceId":"EBAY_GB",
        "format":"FIXED_PRICE",
        "categoryId":"150055",
        "availableQuantity":0,
        "listingDuration":offer.get("listingDuration") or "GTC",
        "listingDescription":offer.get("listingDescription"),
        "pricingSummary":{"price":{"value":"5.79","currency":"GBP"}},
        "listingPolicies":policies,
        "merchantLocationKey":LOCATION_KEY
    }
    inv._request("PUT","/offer/"+offer["offerId"],payload)
    refreshed=inv.offer(offer["offerId"])
    if refreshed.get("status")!="UNPUBLISHED" or refreshed.get("listing") or refreshed.get("availableQuantity")!=0:
        raise DraftError("Unexpected live/stock state; investigate")
    if refreshed.get("merchantLocationKey")!=LOCATION_KEY or any(refreshed.get("listingPolicies",{}).get(k)!=v for k,v in policies.items()):
        raise DraftError("Seller policy/location update not verified")
    print("eBay keyrings: free Royal Mail 2nd Class, UK returns, payment and dispatch location attached.")
    print("Offer still UNPUBLISHED; quantity 0; picture and packed weight pending.")

if __name__=="__main__":
    try:main()
    except (DraftError, OSError, ValueError, KeyError) as e:
        print("KEYRINGS POLICY SETUP FAILED:",e,file=sys.stderr)
        sys.exit(1)
