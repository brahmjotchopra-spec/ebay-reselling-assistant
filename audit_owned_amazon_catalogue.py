"""Read-only check of owned-stock and candidate offers. Never publish or modify listings."""
from ebay_client import Inventory,get_token,DraftError
import sys

SKUS=[
"DRAFT-AMZ-RINGS-25MM-50",
"DRAFT-BULK-JUMP-6MM-100",
"DRAFT-BULK-GRIP-MIX-100",
"DRAFT-BULK-TAGS-MIX-50",
"DRAFT-HOME-MICROFIBRE20",
"DRAFT-HOME-AIRFRYER100",
"DRAFT-HOME-DRAINCATCH100",
"DRAFT-AMZ-PRECISION-SCREW32-1",
"DRAFT-HOME-PETHAIRBRUSH-1",
"DRAFT-AMZ-RUBBERBROOM-120CM-1"
]
def main():
    api=Inventory(get_token());api.check_access()
    for sku in SKUS:
        try:
            offers=api.offers(sku)
            item=api.item(sku)
            if len(offers)!=1:
                print(sku,"OFFERS",len(offers),"INVENTORY_PRESENT",bool(item),flush=True)
                continue
            off=api.offer(offers[0]['offerId'])
            lis=off.get("listing") or {}
            invq=((item or {}).get("availability") or {}).get("shipToLocationAvailability") or {}
            print(sku,"STATUS",off.get("status"),"OFFER_ID",off.get("offerId"),"LISTING_ID",lis.get("listingId"),"OFFER_QTY",off.get("availableQuantity"),"STOCK_QTY",invq.get("quantity"),"IMAGES",len(((item or {}).get("product") or {}).get("imageUrls") or []),flush=True)
        except DraftError as err:
            print(sku,"READ_ERROR",str(err),flush=True)
    print("READ ONLY; no changes",flush=True)
if __name__=="__main__":
    try:main()
    except (DraftError,OSError,ValueError) as err: print("AUDIT_FAILED",str(err),file=sys.stderr);sys.exit(1)
