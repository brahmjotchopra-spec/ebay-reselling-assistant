"""Safely attach verified free UK shipping/return/payment policies to an UNPUBLISHED offer.
No merchantLocationKey is added until actual GoDropship warehouse origin is verified.
No inventory quantity change and no publish API call.
"""
import json, sys
from urllib import request, error
from ebay_client import get_token, DraftError

API="https://api.ebay.com/sell/inventory/v1/offer/347778999011"
PAYMENT_ID="254751987026"
RETURN_ID="254752096026"
FULFILLMENT_ID="254836537026"
def req(method,url,headers,data=None):
    body=None if data is None else json.dumps(data).encode()
    try:
        with request.urlopen(request.Request(url,method=method,data=body,headers=headers),timeout=25) as r:
            raw=r.read()
            return json.loads(raw) if raw else {}
    except error.HTTPError as e:
        try: ids=[str(x.get("errorId")) for x in json.loads(e.read()).get("errors",[])]
        except (ValueError,TypeError): ids=[]
        raise DraftError("eBay "+method+" HTTP "+str(e.code)+" codes "+",".join(ids))
def main():
    h={"Authorization":"Bearer "+get_token(),
       "Content-Language":"en-GB","Content-Type":"application/json"}
    offer=req("GET",API,h)
    if offer.get("sku")!="DRAFT-CAR-46787" or offer.get("status")!="UNPUBLISHED" or offer.get("listing"):
        raise DraftError("Offer not an approved unpublished SKU; cannot update.")
    if offer.get("availableQuantity")!=0:
        raise DraftError("Offer must have zero available stock.")
    policies={"paymentPolicyId":PAYMENT_ID,"returnPolicyId":RETURN_ID,
              "fulfillmentPolicyId":FULFILLMENT_ID}
    if all(offer.get("listingPolicies",{}).get(k)==v for k,v in policies.items()):
        print("POLICIES ALREADY ATTACHED TO UNPUBLISHED OFFER")
        return
    payload={
      "sku":offer["sku"],
      "marketplaceId":"EBAY_GB",
      "format":"FIXED_PRICE",
      "categoryId":offer["categoryId"],
      "availableQuantity":0,
      "listingDuration":offer.get("listingDuration") or "GTC",
      "listingDescription":offer["listingDescription"],
      "pricingSummary":offer["pricingSummary"],
      "listingPolicies":policies,
    }
    # No merchantLocationKey. Using existing home location would misrepresent supplier dispatch.
    req("PUT",API,h,payload)
    latest=req("GET",API,h)
    if latest.get("status")!="UNPUBLISHED" or latest.get("listing") or latest.get("availableQuantity")!=0:
        raise DraftError("Unexpected post-update offer state")
    if not all(latest.get("listingPolicies",{}).get(k)==v for k,v in policies.items()):
        raise DraftError("Listing policy update failed to persist")
    print("ATTACHED 3 SELLER POLICIES. OFFER STILL UNPUBLISHED; quantity zero.")
    print("Merchant location intentionally missing pending exact supplier origin confirmation.")
if __name__=="__main__":
    try:main()
    except (DraftError,KeyError,ValueError,OSError) as e:
        print("POLICY ATTACH FAILED:",e,file=sys.stderr);sys.exit(1)
