"""Stage the Amazon Basics 100-pack black reusable cable strap candidate safely.

Zero buyer-facing stock. Stages only; no publication or supplier purchase.
The six images from this conversation must be manually hosted as exact JPEG
files in assets/cable-straps/ before they are attached. Never silently substitute
a different product gallery.
"""
import json
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-AMZ-BASICS-CABLESTRAPS100"
TITLE="Amazon Basics 100 Reusable Hook and Loop Cable Straps Black Cord Ties"
PRICE="11.99"  # provisional, not an approved net-profit result
SOURCE="https://www.amazon.co.uk/dp/B0BFWJ6P1Z"
BASE="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/cable-straps/"
NAMES=[
  "01-main-product.jpg",
  "02-features.jpg",
  "03-detail-fanned.jpg",
  "04-pack-details.jpg",
  "05-in-use-desk.jpg",
  "06-in-use-closeup.jpg",
]
REFERENCE_SKU="DRAFT-HOME-MICROFIBRE20"
DESCRIPTION=(
 "One Amazon Basics pack containing 100 black reusable hook-and-loop cable straps. "
 "Suitable for organising computer cables, TV leads, chargers and office cords. "
 "Each strap has a threading slot and a hook-and-loop fastening surface. "
 "100 straps are included; no cables or electronic devices are included. "
 "Please check actual pack specifications before purchase. "
 "Gallery includes original digitally created illustrations based on product reference "
 "images, not photographs of the exact physical stock."
)
def taxonomy_id(token):
    root="https://api.ebay.com/commerce/taxonomy/v1"
    hdr={"Authorization":"Bearer "+token,"Accept":"application/json",
         "Accept-Language":"en-GB","X-EBAY-C-MARKETPLACE-ID":"EBAY_GB"}
    def get(path):
        with urlopen(Request(root+path, headers=hdr),timeout=25) as resp:
            return json.load(resp)
    tree=get("/get_default_category_tree_id?marketplace_id=EBAY_GB")["categoryTreeId"]
    names=("cable straps","reusable cable ties","hook and loop cable ties")
    for q in names:
        data=get("/category_tree/"+str(tree)+"/get_category_suggestions?"+urlencode({"q":q}))
        matches=data.get("categorySuggestions") or []
        exact=[m for m in matches if m.get("category",{}).get("categoryName")=="Cable Ties & Organisers"]
        if exact:
            return str(exact[0]["category"]["categoryId"])
    raise DraftError("No verified eBay UK Cable Ties & Organisers category; no offer created")

def gallery_urls():
    files=[]
    for name in NAMES:
        url=BASE+name
        try:
            req=Request(url,method="GET",headers={"User-Agent":"Mozilla/5.0"})
            with urlopen(req,timeout=12) as resp:
                if resp.status!=200 or not resp.read(3).startswith(bytes.fromhex("ffd8ff")):
                    raise DraftError("Incorrect image type: "+name)
        except HTTPError as e:
            if e.code==404:
                print("GALLERY NOT HOSTED: "+name,flush=True)
                return []
            raise DraftError("Unable to check gallery: "+name) from None
        except URLError:
            print("GALLERY CHECK UNAVAILABLE; keeping draft image-free",flush=True)
            return []
        files.append(url)
    return files

def main():
    token=get_token()
    api=Inventory(token)
    api.check_access()
    cats=taxonomy_id(token)
    ref=api.offers(REFERENCE_SKU)
    if len(ref)!=1:
        raise DraftError("No unique live household policy reference")
    reference=api.offer(ref[0]["offerId"])
    pol=reference.get("listingPolicies") or {}
    loc=reference.get("merchantLocationKey")
    fields=("paymentPolicyId","returnPolicyId","fulfillmentPolicyId")
    if reference.get("status")!="PUBLISHED" or not loc or not all(pol.get(f) for f in fields):
        raise DraftError("Seller policy reference not ready")
    existing=api.offers(SKU)
    if len(existing)>1:
        raise DraftError("Duplicate offers detected")
    if existing:
        offer=api.offer(existing[0]["offerId"])
        if offer.get("status")=="PUBLISHED":
            raise DraftError("SKU already live, refusing to alter")
        if offer.get("status")!="UNPUBLISHED" or offer.get("listing"):
            raise DraftError("Unexpected existing offer status")
        if offer.get("categoryId")!=cats or str((offer.get("pricingSummary") or {}).get("price",{}).get("value"))!=PRICE:
            raise DraftError("Draft category or price changed; manual review")
        if offer.get("availableQuantity")!=0:
            raise DraftError("Existing offer has nonzero quantity")
    item=api.item(SKU)
    if item and ((item.get("product") or {}).get("title")!=TITLE or
        (item.get("availability") or {}).get("shipToLocationAvailability",{}).get("quantity")!=0):
        raise DraftError("Existing SKU inventory differs; no changes")
    imgs=gallery_urls()
    product={"title":TITLE,"description":DESCRIPTION,
             "aspects":{"Brand":["Amazon Basics"],"Type":["Hook and Loop Cable Strap"],
                        "Colour":["Black"],"Number in Pack":["100"],"Features":["Reusable"]}}
    if imgs: product["imageUrls"]=imgs
    if not item or imgs:
        api.create_item(SKU,{
            "product":product,
            "condition":"NEW",
            "availability":{"shipToLocationAvailability":{"quantity":0}}
        })
        print("ITEM STORED GALLERY COUNT",len(imgs),flush=True)
    if not existing:
        offer_id=api.create_offer({
            "sku":SKU,"marketplaceId":"EBAY_GB","format":"FIXED_PRICE",
            "categoryId":cats,"availableQuantity":0,"listingDuration":"GTC",
            "listingDescription":DESCRIPTION,
            "pricingSummary":{"price":{"value":PRICE,"currency":"GBP"}},
            "listingPolicies":{k:pol[k] for k in fields},"merchantLocationKey":loc
        })
    else:
        offer_id=existing[0]["offerId"]
    checked=api.offer(offer_id)
    if checked.get("status")!="UNPUBLISHED" or checked.get("availableQuantity")!=0 or checked.get("listing"):
        raise DraftError("Readback unexpectedly indicates a live orderable listing")
    print("VERIFIED UNPUBLISHED EBAY OFFER",offer_id,"SKU",SKU,flush=True)
    print("QTY 0 / NO LIVE LISTING / NO PAYMENT / NO SPEND",flush=True)
    if not imgs:
        print("PHOTO BLOCKER: user image JPG files have not been hosted in assets/cable-straps/",flush=True)
    print("PUBLICATION BLOCKERS: physical inventory, source price/Locker, delivery dimensions, fees and image gallery",flush=True)

if __name__=="__main__":
    try:main()
    except (DraftError,HTTPError,URLError,ValueError,TypeError,KeyError,OSError) as exc:
        print("CABLE STRAP STAGING STOPPED",str(exc),file=sys.stderr)
        sys.exit(1)
