"""Publish ONE owned 10-piece lot of red/black double-sided foam plate pads.

User confirms holding one original 50-pack on 22 Nov 2026; offer is for
10 individually supplied 90 x 20 x 2 mm pads ONLY. Other 40 are not in
this offer. Never buy stock or retailer-to-customer dropship.
Uses original clearly disclosed illustrations, not stock photography.
Price: £3.99. Exactly one buyer-orderable 10-pad lot.
"""
import sys,time,json
from urllib.parse import quote,urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-PLATE-STICKYPADS10-1"
PRICE="3.99"
QTY=1
TITLE="10 x Number Plate Sticky Pads Double Sided Foam Adhesive Tape 90x20x2mm"
DESCRIPTION=(
    "ONE lot of TEN (10) pre-cut double-sided foam adhesive sticky pads suitable "
    "for fixing vehicle registration number plates to compatible flat mounting "
    "surfaces. Each strip measures approximately 90 mm long x 20 mm wide x 2 mm "
    "thick. Red removable protective release liner over dark foam adhesive. "
    "Simple peel-and-stick installation; prepare a clean, dry, grease-free "
    "surface and confirm secure adhesion before driving. Adhesion depends on "
    "surfaces and conditions. Contents: 10 adhesive strips only, supplied "
    "as a counted lot from a larger original retail pack. "
    "Not 50 strips. No number plate, vehicle or accessories included. "
    "Images are ORIGINAL DIGITAL PRODUCT ILLUSTRATIONS to explain the design "
    "and use, NOT photographs of the exact received stock. "
    "Product dimensions and colour may vary slightly."
)
BASE="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/number-plate-pads/"
FILES=["01-main-10-pads.jpg","02-quantity-10.jpg","03-exact-dimensions.jpg",
       "04-peel-and-stick-detail.jpg","05-number-plate-example.jpg",
       "06-pack-contents.jpg"]
IMAGES=[BASE+n for n in FILES]
POLICY_KEYS=("paymentPolicyId","returnPolicyId","fulfillmentPolicyId")
REFERENCE_SKU="DRAFT-HOME-MICROFIBRE20"

def verify_images():
    if len(IMAGES)!=6 or len(set(IMAGES))!=6:
        raise DraftError("Six distinct eBay image URLs required")
    for url in IMAGES:
        for _ in range(15):
            try:
                with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=12) as response:
                    if (response.status==200 and
                        response.headers.get("Content-Type","").startswith("image/jpeg") and
                        response.read(3)==bytes.fromhex("ffd8ff")):
                        break
            except (URLError,HTTPError,TimeoutError):
                pass
            time.sleep(3)
        else:
            raise DraftError("Listing image not publicly served as JPEG: "+url)
    print("SIX ORIGINAL NUMBER PLATE PAD IMAGES PUBLIC AND VALID",flush=True)

def find_category(token):
    root="https://api.ebay.com/commerce/taxonomy/v1"
    headers={"Authorization":"Bearer "+token,"Accept":"application/json",
             "X-EBAY-C-MARKETPLACE-ID":"EBAY_GB",
             "Accept-Language":"en-GB"}
    def get(path):
        with urlopen(Request(root+path,headers=headers),timeout=22) as f:
            return json.load(f)
    tree=get("/get_default_category_tree_id?marketplace_id=EBAY_GB")["categoryTreeId"]
    possibilities=[]
    for q in ("number plate sticky pads","number plate fixing pads",
              "number plates surrounds","car number plate adhesives"):
        found=get("/category_tree/"+str(tree)+"/get_category_suggestions?"+urlencode({"q":q})).get("categorySuggestions") or []
        for s in found:
            cat=s.get("category") or {}
            name=cat.get("categoryName") or ""
            ancestors=[a.get("categoryName","") for a in s.get("categoryTreeNodeAncestors") or []]
            cid=cat.get("categoryId")
            if cid:possibilities.append((name,str(cid),ancestors))
        for name,cid,anc in possibilities:
            if name in ("Number Plates & Surrounds","Number Plates, Frames & Accessories","Number Plate Accessories"):
                print("SELECTED EBAY UK CATEGORY",cid,name,flush=True)
                return cid
    for name,cid,anc in possibilities:
        if "number plate" in name.lower() and not any(k in name.lower() for k in ("motorcycle","motorbike","bike","truck","van")):
            print("SELECTED EBAY UK CATEGORY",cid,name,flush=True)
            return cid
    print("CATEGORY SUGGESTIONS",possibilities[:20],flush=True)
    raise DraftError("Could not verify appropriate UK category for number plate adhesive pads")

def main():
    token=get_token()
    api=Inventory(token)
    api.check_access()
    offers=api.offers(SKU)
    if len(offers)>1:raise DraftError("Multiple offers found for one SKU; refuse duplicate")
    if offers:
        offer=api.offer(offers[0]["offerId"])
        if offer.get("status")=="PUBLISHED":
            lid=(offer.get("listing") or {}).get("listingId")
            if not lid:raise DraftError("Already live but listing ID missing")
            print("ALREADY LIVE - NO DUPLICATE https://www.ebay.co.uk/itm/"+str(lid),flush=True)
            return
        if offer.get("status")!="UNPUBLISHED" or offer.get("listing"):
            raise DraftError("Unexpected existing offer state")
        if str(((offer.get("pricingSummary") or {}).get("price") or {}).get("value"))!=PRICE:
            raise DraftError("Price changed on previously created offer")
        existing_item=api.item(SKU)
        if not existing_item or (existing_item.get("product") or {}).get("title")!=TITLE:
            raise DraftError("Existing inventory not the correct product")
    verify_images()
    category=find_category(token)
    refs=api.offers(REFERENCE_SKU)
    if len(refs)!=1:raise DraftError("Unique existing seller policy reference not found")
    reference=api.offer(refs[0]["offerId"])
    pol=reference.get("listingPolicies") or {}
    location=reference.get("merchantLocationKey")
    if reference.get("status")!="PUBLISHED" or not location or not all(pol.get(k) for k in POLICY_KEYS):
        raise DraftError("Seller reference not published or missing policies")
    locations=api._request("GET","/location?limit=100").get("locations") or []
    if not any(x.get("merchantLocationKey")==location and x.get("merchantLocationStatus")=="ENABLED" for x in locations):
        raise DraftError("Seller dispatch location disabled")
    policies={k:pol[k] for k in POLICY_KEYS}
    if offers and offer.get("categoryId")!=category:
        raise DraftError("Category changed in existing offer")
    product={
        "title":TITLE,
        "description":DESCRIPTION,
        "imageUrls":IMAGES,
        "aspects":{
          "Brand":["Unbranded"],"Type":["Number Plate Adhesive Pads"],
          "Colour":["Red"],"Material":["Foam"],
          "Size":["90 mm x 20 mm x 2 mm"],"Number in Pack":["10"]
        }
    }
    existing=api.item(SKU)
    if existing and (existing.get("product") or {}).get("title")!=TITLE:
        raise DraftError("SKU already used by other product")
    if existing and (existing.get("availability") or {}).get("shipToLocationAvailability",{}).get("quantity") not in (0,QTY):
        raise DraftError("Existing quantity unexpected")
    api.create_item(SKU,{"product":product,"condition":"NEW",
                         "availability":{"shipToLocationAvailability":{"quantity":QTY}}})
    stored=api.item(SKU)
    if ((stored.get("product") or {}).get("imageUrls")!=IMAGES or
        (stored.get("availability") or {}).get("shipToLocationAvailability",{}).get("quantity")!=QTY):
        raise DraftError("Inventory/gallery/stock readback mismatch")
    offer_payload={
        "sku":SKU,"marketplaceId":"EBAY_GB","format":"FIXED_PRICE",
        "categoryId":category,"availableQuantity":QTY,"listingDuration":"GTC",
        "listingDescription":DESCRIPTION,
        "pricingSummary":{"price":{"value":PRICE,"currency":"GBP"}},
        "listingPolicies":policies,
        "merchantLocationKey":location
    }
    if offers:
        oid=offers[0]["offerId"]
        api._request("PUT","/offer/"+oid,offer_payload)
    else:
        oid=api.create_offer(offer_payload)
    before=api.offer(oid)
    if (before.get("status")!="UNPUBLISHED" or before.get("listing") or
        before.get("availableQuantity")!=QTY or
        str(((before.get("pricingSummary") or {}).get("price") or {}).get("value"))!=PRICE):
        raise DraftError("Offer verification before publication failed")
    print("PREPUBLISH CHECK PASSED; 10-piece lot, 6 images, £3.99, qty1",flush=True)
    result=api._request("POST","/offer/"+oid+"/publish")
    lid=result.get("listingId")
    if not lid:raise DraftError("No listingId returned; inspect live state before retry")
    after=api.offer(oid)
    if after.get("status")!="PUBLISHED" or str((after.get("listing") or {}).get("listingId"))!=str(lid):
        raise DraftError("eBay listing published but readback verification differed")
    print("SUCCESS PUBLISHED https://www.ebay.co.uk/itm/"+str(lid),flush=True)
    print("EBAY OFFER",oid,"PRICE GBP",PRICE,"STOCK LOTS",QTY,"PADS PER LOT",10,"PHOTO COUNT",len(IMAGES),flush=True)
    print("User must count 10 from owned 50 pack, pack flat and fulfil dispatch policy",flush=True)

if __name__=="__main__":
    try: main()
    except (DraftError,ValueError,KeyError,TypeError,OSError,URLError,HTTPError) as exc:
        print("PLATE PAD PUBLICATION STOPPED:",str(exc),file=sys.stderr)
        sys.exit(1)
