"""Diagnose / retry only the existing 100-drain-catcher eBay listing, read safe errors."""
import json,sys
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from ebay_client import Inventory,DraftError,get_token
SKU="DRAFT-HOME-DRAINCATCH100"
PRICE="7.99"
def main():
    token=get_token()
    api=Inventory(token)
    offers=api.offers(SKU)
    if len(offers)!=1:raise DraftError("Expected one offer")
    offer=api.offer(offers[0]["offerId"])
    if offer.get("status")=="PUBLISHED":
        lid=(offer.get("listing") or {}).get("listingId")
        print("ALREADY LIVE https://www.ebay.co.uk/itm/"+str(lid),flush=True)
        return
    item=api.item(SKU)
    price=(offer.get("pricingSummary") or {}).get("price") or {}
    if (offer.get("status")!="UNPUBLISHED" or offer.get("listing") or
        offer.get("sku")!=SKU or price.get("value")!=PRICE or
        not item or item.get("product",{}).get("imageUrls") is None):
        raise DraftError("Unexpected prior state; refusing attempt")
    print("DRAIN OFFER ID",offer["offerId"],"category",offer.get("categoryId"),"images",len(item.get("product",{}).get("imageUrls",[])),flush=True)
    request=Request("https://api.ebay.com/sell/inventory/v1/offer/"+offer["offerId"]+"/publish",data=None,
                    method="POST",headers={"Authorization":"Bearer "+token,"Content-Type":"application/json",
                                           "Accept":"application/json","Content-Language":"en-GB"})
    try:
        with urlopen(request,timeout=28) as resp:
            body=json.loads(resp.read())
            print("PUBLISH RESPONSE",json.dumps(body,ensure_ascii=False)[:2000],flush=True)
    except HTTPError as exc:
        try:
            result=json.loads(exc.read().decode("utf8"))
        except (ValueError,UnicodeError):
            result={}
        errors=[]
        for error in result.get("errors",[]):
            errors.append({key:error.get(key) for key in
                           ("errorId","message","longMessage","parameters","category") if error.get(key) is not None})
        print("PUBLISH FAILED HTTP",exc.code,"DETAILS",json.dumps(errors,ensure_ascii=False)[:6000],flush=True)
        return
    if body.get("listingId"):
        after=api.offer(offers[0]["offerId"])
        if after.get("status")=="PUBLISHED" and str((after.get("listing") or {}).get("listingId"))==str(body["listingId"]):
            print("PUBLISHED AND VERIFIED https://www.ebay.co.uk/itm/"+str(body["listingId"]),flush=True)
            return
    print("UNKNOWN RESULT, CHECK OFFER STATE",flush=True)
if __name__=="__main__":
    try:main()
    except (DraftError,ValueError,KeyError,OSError) as exc:
        print("DIAGNOSTIC STOPPED:",exc,file=sys.stderr)
        sys.exit(1)
