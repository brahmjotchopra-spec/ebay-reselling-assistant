"""Create idempotent NON-LIVE eBay UK offers for researched retail bulk candidates.

All offers have zero available stock. No user has stated these products are already
owned. This script cannot publish, order goods, or promise dispatch.
"""
import json,sys
from pathlib import Path
from ebay_client import Inventory, get_token, DraftError
from ebay_bot import payloads, ensure_draft

SOURCE=Path("research/amazon-bulk-stage.json")
SKUS={"BULK-JUMP-6MM-100","BULK-GRIP-MIX-100","BULK-TAGS-MIX-50"}

def main():
    rows=json.loads(SOURCE.read_text("utf-8"))
    if len(rows)!=3 or set(x["sku"] for x in rows)!=SKUS:
        raise DraftError("Candidate set differs; refusing to stage")
    for x in rows:
        if x.get("stock")!=0 or x.get("amazon_locker_verified") is not False or x.get("approved_for_unpublished_offer") is not False:
            raise DraftError("Every staged candidate must remain unverified, unapproved and at zero stock")
        if x.get("category_id") not in ("150055","86174","184488"):
            raise DraftError("Unknown category")
        inv,offer=payloads(x)
        if inv["availability"]["shipToLocationAvailability"]["quantity"]!=0 or offer["availableQuantity"]!=0:
            raise DraftError("Unexpected positive quantity")
    api=Inventory(get_token())
    api.check_access()
    for x in rows:
        inv,offer=payloads(x)
        state,offer_id=ensure_draft(api,inv,offer)
        if offer_id and state in ("created and verified","already verified"):
            print("STAGED NONLIVE:",x["sku"],"Price GBP",x["price_gbp"],"State",state,"Inventory quantity zero")
        else:
            raise DraftError("Offer state could not be verified")
    print("All three researched candidate offers remain unpublished with stock zero. No buyer orders can be taken.")

if __name__=="__main__":
    try:main()
    except (DraftError,ValueError,KeyError,OSError) as e:
        print("STAGING ERROR:",e,file=sys.stderr)
        sys.exit(1)
