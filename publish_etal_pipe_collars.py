"""Publish one seller-confirmed ETAL 15mm white pipe collar 10-pack."""
import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from ebay_client import Inventory, DraftError, get_token

SKU="ETAL-336AK-WHITE-15MM-10"
PRICE="6.49"
QTY=1
TITLE="10x ETAL White 15mm Radiator Pipe Collars Snap On Floor Wall Pipe Covers"
DESCRIPTION=("One new pack of 10 white ETAL uPVC pipe collars. Snap-on design for pipes with a 15 mm outside diameter. Covers gaps around exposed pipework at floor or wall level. Check pipe diameter before ordering. Ten collars only; pipe and radiator are not included. Gallery shows cropped supplier product references.")
IMAGE_PATHS=["assets/etal-pipe-collars/etal-0.jpg","assets/etal-pipe-collars/etal-1.jpg"]
IMAGE_URLS=["https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/"+os.environ.get("IMAGE_COMMIT","main")+"/"+p for p in IMAGE_PATHS]
REFERENCE_SKU="DRAFT-HOME-MICROFIBRE20"
FIELDS=("paymentPolicyId","returnPolicyId","fulfillmentPolicyId")

def category(token):
    root="https://api.ebay.com/commerce/taxonomy/v1"
    hdr={"Authorization":"Bearer "+token,"Accept":"application/json","Accept-Language":"en-GB"}
    def get(path):
        with urlopen(Request(root+path,headers=hdr),timeout=25) as response:
            return json.load(response)
    tree=get("/get_default_category_tree_id?marketplace_id=EBAY_GB")["categoryTreeId"]
    for q in ("15mm radiator pipe collars","radiator pipe collar snap on","plumbing pipe collars"):
        data=get("/category_tree/"+str(tree)+"/get_category_suggestions?"+urlencode({"q":q}))
        for suggestion in data.get("categorySuggestions",[]):
            c=suggestion.get("category",{})
            if c.get("categoryName") in ("Other Home Plumbing & Fixtures","Other Plumbing & Fixtures","Pipe Fittings","Pipe Fittings & Accessories","Radiator Accessories","Radiator Pipe Collars","Other Heating, Cooling & Air","Radiators & Accessories","Other Plumbing"):
                print("CATEGORY",c,flush=True)
                return str(c["categoryId"])
    raise DraftError("Correct eBay category not confirmed.")

def main():
    for path,url in zip(IMAGE_PATHS,IMAGE_URLS):
        local=Path(path)
        if not local.is_file() or local.read_bytes()[:3]!=bytes.fromhex("ffd8ff"):
            raise DraftError("Approved JPEG missing. No eBay write performed.")
        for attempt in range(5):
            try:
                with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=20) as resp:
                    if resp.read()==local.read_bytes(): break
            except OSError:
                pass
            if attempt==4: raise DraftError("Public gallery does not match approved file.")
            time.sleep(4)
    token=get_token()
    api=Inventory(token)
    api.check_access()
    existing=api.offers(SKU)
    if len(existing)>1:
        raise DraftError("Multiple offers; refusing duplicate.")
    offer=api.offer(existing[0]["offerId"]) if existing else None
    if offer and offer.get("status")=="PUBLISHED":
        listing=(offer.get("listing") or {}).get("listingId")
        if not listing: raise DraftError("Published state without listing ID.")
        print("ALREADY LIVE https://www.ebay.co.uk/itm/"+str(listing))
        return
    cat=category(token)
    refs=api.offers(REFERENCE_SKU)
    if len(refs)!=1: raise DraftError("Seller policy reference not unique.")
    ref=api.offer(refs[0]["offerId"])
    pol=ref.get("listingPolicies") or {}
    loc=ref.get("merchantLocationKey")
    if ref.get("status")!="PUBLISHED" or not loc or not all(pol.get(k) for k in FIELDS):
        raise DraftError("Existing live dispatch policy missing.")
    locs=api._request("GET","/location?limit=100").get("locations",[])
    if not any(x.get("merchantLocationKey")==loc and x.get("merchantLocationStatus")=="ENABLED" for x in locs):
        raise DraftError("Dispatch location not enabled.")
    product={"title":TITLE,"description":DESCRIPTION,"imageUrls":IMAGE_URLS,
             "aspects":{"Brand":["ETAL"],"Type":["Collars"],"Colour":["White"],"Material":["Plastic"],"Shape":["Round"],"Number in Pack":["10"],"Suitable Pipe Diameter":["15 mm"]}}
    old=api.item(SKU)
    if old and ((old.get("product") or {}).get("title")!=TITLE or old.get("condition")!="NEW"):
        raise DraftError("Existing inventory differs; no overwrite.")
    if offer and (offer.get("status")!="UNPUBLISHED" or offer.get("listing") or offer.get("categoryId")!=cat or str(((offer.get("pricingSummary") or {}).get("price") or {}).get("value"))!=PRICE):
        raise DraftError("Existing offer differs; manual review.")
    api.create_item(SKU,{"product":product,"condition":"NEW","availability":{"shipToLocationAvailability":{"quantity":QTY}}})
    payload={"sku":SKU,"marketplaceId":"EBAY_GB","format":"FIXED_PRICE","categoryId":cat,"availableQuantity":QTY,"listingDuration":"GTC","listingDescription":DESCRIPTION,"pricingSummary":{"price":{"value":PRICE,"currency":"GBP"}},"listingPolicies":{k:pol[k] for k in FIELDS},"merchantLocationKey":loc}
    if offer:
        oid=offer["offerId"]
        api._request("PUT","/offer/"+oid,payload)
    else:
        oid=api.create_offer(payload)
    before=api.offer(oid)
    item=api.item(SKU)
    if before.get("status")!="UNPUBLISHED" or before.get("availableQuantity")!=QTY or (item.get("product") or {}).get("imageUrls")!=IMAGE_URLS or ((item.get("availability") or {}).get("shipToLocationAvailability") or {}).get("quantity")!=QTY:
        raise DraftError("Offer/gallery readback failed; no publication.")
    result=api._request("POST","/offer/"+oid+"/publish")
    listing=result.get("listingId")
    after=api.offer(oid)
    if not listing or after.get("status")!="PUBLISHED" or str((after.get("listing") or {}).get("listingId"))!=str(listing):
        raise DraftError("Publication not verified; reconcile before retry.")
    print("VERIFIED LIVE https://www.ebay.co.uk/itm/"+str(listing))

if __name__=="__main__":
    main()
