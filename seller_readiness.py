"""Read-only eBay seller configuration probe; no personal address or bearer token output."""
import os,json,urllib.request,urllib.error
from ebay_client import get_token, DraftError

def get(url,headers):
    r=urllib.request.Request(url,headers=headers,method="GET")
    try:
        with urllib.request.urlopen(r,timeout=20) as res:
            return (res.status,json.load(res))
    except urllib.error.HTTPError as ex:
        raw=ex.read()
        try:
            payload=json.loads(raw)
            ids=[str(e.get("errorId")) for e in payload.get("errors",[]) if isinstance(e,dict)]
        except (ValueError,TypeError):
            ids=[]
        return (ex.code,{"ids":ids})
    except Exception as e:
        return ("NETWORK_ERROR",{})

def probe():
    token=get_token()
    headers={"Authorization":"Bearer "+token,"Accept":"application/json","Content-Language":"en-GB"}
    calls={
        "inventory_locations":"https://api.ebay.com/sell/inventory/v1/location?limit=20",
        "fulfillment_policies":"https://api.ebay.com/sell/account/v1/fulfillment_policy?marketplace_id=EBAY_GB",
        "payment_policies":"https://api.ebay.com/sell/account/v1/payment_policy?marketplace_id=EBAY_GB",
        "return_policies":"https://api.ebay.com/sell/account/v1/return_policy?marketplace_id=EBAY_GB",
        "selling_programs":"https://api.ebay.com/sell/account/v1/program/get_opted_in_programs",
        "offer_347778999011":"https://api.ebay.com/sell/inventory/v1/offer/347778999011",
    }
    for name,url in calls.items():
        code,data=get(url,headers)
        print(name,"HTTP",code)
        if code==200:
            if name=="inventory_locations":
                vals=data.get("locations",[])
                print("  locations:",[{"key":x.get("merchantLocationKey"),"status":x.get("merchantLocationStatus"),"type":x.get("locationTypes")} for x in vals])
            elif name.endswith("_policies"):
                for key in ("fulfillmentPolicies","paymentPolicies","returnPolicies"):
                    if key in data:
                        print("  policies:",[{"name":x.get("name"),"policyId":x.get(key[:-3]+"Id")} for x in data[key]])
                if not any(key in data for key in ("fulfillmentPolicies","paymentPolicies","returnPolicies")):
                    print("  response keys:",list(data))
            elif name=="selling_programs":
                print("  enrolled programs:",[x.get("programType") for x in data.get("programs",[])])
            elif name.startswith("offer_"):
                print("  offer:",{"status":data.get("status"),"listing":bool(data.get("listing")),"merchantLocationKey":data.get("merchantLocationKey"),"policies_present":list(data.get("listingPolicies",{}).keys()),"quantity":data.get("availableQuantity"),"sku":data.get("sku")})
        else:
            print("  error_ids:",data.get("ids",[]))
if __name__=="__main__":
    probe()
