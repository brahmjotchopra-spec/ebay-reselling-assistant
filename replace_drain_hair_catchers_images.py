"""Replace photos on live 100 drain-sticker/6 scraper eBay listing.

This job is triggered only once the seller uploads the approved two-photo ZIP to
assets/. It never creates another listing and preserves price, stock and policies.
"""
import io
import json
import sys
import time
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from ebay_client import Inventory, DraftError, get_token

SKU="DRAFT-HOME-DRAINCATCH100"
LISTING_ID="880140085248"
PRICE="7.99"
ZIP=Path("assets/drain_gallery_upload_to_github.zip")
ROOT="https://raw.githubusercontent.com/brahmjotchopra-spec/ebay-reselling-assistant/main/assets/"
FILENAMES=["drain_main.jpg","drain_sizes.jpg"]
URLS=[ROOT+name for name in FILENAMES]
TITLE="100 Shower Drain Hair Catcher Mesh Stickers 10x10cm + 6 Scrapers"
DESCRIPTION=(
    "Bundle of 100 disposable 10 x 10 cm square white adhesive mesh hair-catcher stickers "
    "and 6 yellow plastic scraper tools. Designed for compatible flat shower and bath "
    "drains to catch loose hair. Apply to a clean, dry area and ensure the sticker is "
    "securely attached. This listing is for the 100 mesh stickers and 6 scraper tools "
    "only; drain fitting and other pictured accessories are not included. "
    "The images are digitally created visual illustrations of the product type."
)
def verify_assets():
    if not ZIP.exists():
        raise DraftError("Photo ZIP has not been uploaded to assets/ in GitHub; not updating the listing")
    with zipfile.ZipFile(ZIP) as z:
        if set(z.namelist())!=set(FILENAMES):
            raise DraftError("Photo ZIP must contain only drain_main.jpg and drain_sizes.jpg")
        for name in FILENAMES:
            data=z.read(name)
            if not data.startswith(bytes.fromhex("ffd8ff")) or len(data)<30000:
                raise DraftError("Invalid low-resolution photo: "+name)
            Path("assets",name).write_bytes(data)
            print("PREPARED PHOTO",name,len(data),flush=True)

def remote_image(url):
    for _ in range(10):
        try:
            with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=15) as resp:
                if resp.status==200 and resp.read(3)==bytes.fromhex("ffd8ff"):
                    return
        except (HTTPError,URLError,OSError):pass
        time.sleep(2)
    raise DraftError("Approved new photo not available at GitHub: "+url.rsplit("/",1)[-1])

def main():
    for url in URLS:remote_image(url)
    api=Inventory(get_token())
    api.check_access()
    candidates=api.offers(SKU)
    if len(candidates)!=1: raise DraftError("Expected one drain catcher offer")
    offer=api.offer(candidates[0]["offerId"])
    if offer.get("status")!="PUBLISHED" or offer.get("sku")!=SKU or str((offer.get("listing") or {}).get("listingId"))!=LISTING_ID:
        raise DraftError("Live listing identity mismatch")
    price=(offer.get("pricingSummary") or {}).get("price") or {}
    if price.get("currency")!="GBP" or str(price.get("value"))!=PRICE:
        raise DraftError("Price differs from £7.99; refusing modification")
    item=api.item(SKU)
    if not item or item.get("condition")!="NEW":
        raise DraftError("Expected new-condition inventory")
    product=dict(item.get("product") or {})
    if not (product.get("title") or "").startswith("100 Disposable Shower Drain Hair Catcher"):
        if product.get("imageUrls")==URLS and product.get("title")==TITLE:
            print("ALREADY UPDATED; NO DUPLICATE: https://www.ebay.co.uk/itm/"+LISTING_ID,flush=True)
            return
        raise DraftError("Unexpected product title; refusing modification")
    oldimages=product.get("imageUrls") or []
    if len(oldimages)!=1 or "household-drain-hair-catchers-100.jpg" not in oldimages[0]:
        raise DraftError("Existing image set changed, refusing overwrite")
    stock=(item.get("availability") or {}).get("shipToLocationAvailability",{}).get("quantity")
    if stock!=1 or offer.get("availableQuantity")!=1:
        raise DraftError("Stock has changed; refuse modification")
    product["title"]=TITLE
    product["description"]=DESCRIPTION
    product["imageUrls"]=URLS
    # Preserve brand/MPN, colour, material and category.
    body={"product":product,"condition":"NEW","availability":item["availability"]}
    for k in ("conditionDescription","packageWeightAndSize"):
        if k in item: body[k]=item[k]
    api.create_item(SKU,body)
    after_item=api.item(SKU)
    if ((after_item.get("product") or {}).get("imageUrls")!=URLS or
       (after_item.get("product") or {}).get("title")!=TITLE or
       after_item.get("availability",{}).get("shipToLocationAvailability",{}).get("quantity")!=stock):
        raise DraftError("Inventory image/title verification failed")
    # Keep the eBay offer's description synchronized with updated bundle contents.
    policies=offer.get("listingPolicies") or {}
    if not all(policies.get(k) for k in ("paymentPolicyId","returnPolicyId","fulfillmentPolicyId")):
        raise DraftError("Missing seller policies")
    offer_body={
      "sku":SKU,"marketplaceId":"EBAY_GB","format":"FIXED_PRICE",
      "categoryId":offer["categoryId"],"availableQuantity":stock,
      "listingDuration":offer.get("listingDuration") or "GTC",
      "listingDescription":DESCRIPTION,
      "pricingSummary":{"price":{"value":PRICE,"currency":"GBP"}},
      "listingPolicies":policies,"merchantLocationKey":offer["merchantLocationKey"]
    }
    api._request("PUT","/offer/"+offer["offerId"],offer_body)
    after=api.offer(offer["offerId"])
    if (after.get("status")!="PUBLISHED" or
        str((after.get("listing") or {}).get("listingId"))!=LISTING_ID or
        after.get("pricingSummary",{}).get("price")!=price or
        after.get("availableQuantity")!=stock):
        raise DraftError("Live listing status/price/stock not verified")
    print("SUCCESS: TWO NEW PHOTOS AND CORRECTED CONTENT ON LIVE EBAY LISTING",flush=True)
    print("LISTING https://www.ebay.co.uk/itm/"+LISTING_ID,flush=True)
    print("PRICE £"+PRICE+" QUANTITY "+str(stock),flush=True)
    print("IMAGES "+", ".join(URLS),flush=True)

if __name__=="__main__":
    try: main()
    except (DraftError,ValueError,KeyError,OSError,TypeError) as exc:
        print("DRAIN IMAGE UPDATE STOPPED:",exc,file=sys.stderr)
        sys.exit(1)
