"""Prepare an additional FREE tracked UK postage policy; never touch existing policies."""
import json, sys
from urllib import request, error
from ebay_client import get_token, DraftError

BASE="https://api.ebay.com/sell/account/v1/fulfillment_policy"
NAME="GoDropship UK Tracked 48 - Free Postage"
def call(method, url, headers, payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    r=request.Request(url,method=method,data=data,headers=headers)
    try:
        with request.urlopen(r,timeout=25) as f:
            raw=f.read()
            return json.loads(raw) if raw else {}
    except error.HTTPError as e:
        body=e.read()
        try:
            ids=[x.get("errorId") for x in json.loads(body).get("errors",[])]
        except (ValueError,TypeError):
            ids=[]
        raise DraftError("eBay policy API rejected "+method+" HTTP "+str(e.code)+" codes "+str(ids))

def main():
    headers={"Authorization":"Bearer "+get_token(),"Content-Type":"application/json","Content-Language":"en-GB"}
    current=call("GET",BASE+"?marketplace_id=EBAY_GB",headers)
    for x in current.get("fulfillmentPolicies",[]):
        if x.get("name")==NAME:
            print("ALREADY EXISTS:",NAME,"ID",x.get("fulfillmentPolicyId"))
            return
    payload={
      "name": NAME,
      "marketplaceId":"EBAY_GB",
      "categoryTypes":[{"name":"ALL_EXCLUDING_MOTORS_VEHICLES"}],
      "handlingTime":{"value":2,"unit":"DAY"},
      "shippingOptions":[{
        "optionType":"DOMESTIC","costType":"FLAT_RATE",
        "shippingServices":[{
          "shippingServiceCode":"UK_RoyalMailTracked",
          "shippingCarrierCode":"RoyalMail",
          "freeShipping":True,
          "shippingCost":{"value":"0.00","currency":"GBP"}
        }]
      }]
    }
    result=call("POST",BASE,headers,payload)
    policy_id=result.get("fulfillmentPolicyId")
    if not policy_id: raise DraftError("No new policy ID returned")
    print("CREATED FREE UK POLICY",NAME,"ID",policy_id)
    print("Scope: Royal Mail Tracked 48, 2-day handling, £0 delivery. No listing published.")
if __name__=="__main__":
    try:main()
    except (DraftError,OSError,ValueError) as e:
        print("POLICY NOT CREATED:",e,file=sys.stderr)
        sys.exit(1)
