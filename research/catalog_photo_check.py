"""Read-only eBay UK catalogue search for three owned-stock resale lots.

Only eBay catalogue assets may be reused. Do not copy Amazon or other sellers' pictures.
Catalogue image search cannot itself establish an exact match for a repacked lot.
"""
import json, sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from ebay_client import get_token, DraftError

QUERIES = [
    ("JUMP RINGS", "PandaHall 6mm Stainless Steel Open Jump Rings 1000"),
    ("GRIP BAGS", "mawmuaw 500 Small Resealable Grip Seal Bags 5 Sizes"),
    ("GIFT TAGS", "CHSYOO 300 Brown White Black Round Kraft Paper Gift Tags 6cm"),
]
BASE="https://api.ebay.com/commerce/catalog/v1_beta/product_summary/search"

def main():
    token=get_token()
    for label,q in QUERIES:
        req=Request(BASE+"?"+urlencode({"q":q,"limit":"10"}),headers={
            "Authorization":"Bearer "+token,"Accept":"application/json",
            "Content-Language":"en-GB","X-EBAY-C-MARKETPLACE-ID":"EBAY_GB",
        })
        try:
            with urlopen(req,timeout=25) as resp:
                body=json.loads(resp.read())
        except HTTPError as exc:
            try:
                errors=json.loads(exc.read()).get("errors",[])
                codes=[e.get("errorId") for e in errors]
            except (ValueError, TypeError, AttributeError):
                codes=[]
            print(label+": catalog API unavailable HTTP "+str(exc.code)+" codes "+repr(codes))
            continue
        except (URLError,OSError,ValueError) as exc:
            print(label+": catalog read failed ("+type(exc).__name__+")")
            continue
        products=body.get("productSummaries",[])
        print(label+": "+str(len(products))+" eBay catalogue candidate(s), exact match NOT established")
        for p in products[:10]:
            img=(p.get("image") or {}).get("imageUrl")
            print(json.dumps({"title":p.get("title"),"brand":p.get("brand"),"mpn":p.get("mpn"),"gtin":p.get("gtin"),"epid":p.get("epid"),"image":img},ensure_ascii=True))
    print("No published listings or inventory changes. Catalogue pictures can be used only for exact product/pack matches.")

if __name__=="__main__":
    try:
        main()
    except (DraftError,ValueError,OSError) as exc:
        print("Catalogue check stopped:",exc,file=sys.stderr)
        sys.exit(1)
