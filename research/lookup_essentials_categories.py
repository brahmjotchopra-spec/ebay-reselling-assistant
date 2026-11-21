"""Read-only eBay UK leaf-category suggestions for household essentials."""
import sys,json
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from ebay_client import get_token,DraftError

ROOT="https://api.ebay.com/commerce/taxonomy/v1"
QUERIES={
 "microfibre_cloths":"microfibre cleaning cloths",
 "air_fryer_liners":"air fryer paper liners",
 "shower_drain_catchers":"shower drain hair catcher",
}
def req(url,token):
    request=Request(url,headers={"Authorization":"Bearer "+token,
                                 "Content-Type":"application/json",
                                 "Accept":"application/json",
                                 "Accept-Language":"en-GB",
                                 "X-EBAY-C-MARKETPLACE-ID":"EBAY_GB"})
    try:
        with urlopen(request,timeout=25) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        raw=exc.read().decode("utf-8","replace")
        raise DraftError(f"Taxonomy API HTTP {exc.code}: "+raw[:500]) from None

def main():
    token=get_token()
    tree=req(ROOT+"/get_default_category_tree_id?marketplace_id=EBAY_GB",token).get("categoryTreeId")
    if not tree: raise DraftError("No EBAY_GB category tree ID")
    print("UK_CATEGORY_TREE",tree)
    for key,query in QUERIES.items():
        data=req(ROOT+"/category_tree/"+str(tree)+"/get_category_suggestions?"+urlencode({"q":query}),token)
        suggested=data.get("categorySuggestions") or []
        if not suggested:raise DraftError("No category suggestions for "+key)
        print("ITEM",key,"SUGGESTIONS",json.dumps(
            [{"id":s.get("category",{}).get("categoryId"),
              "name":s.get("category",{}).get("categoryName"),
              "level":s.get("categoryTreeNodeLevel"),
              "ancestors":[p.get("categoryName") for p in s.get("categoryTreeNodeAncestors",[])]}
             for s in suggested[:8]],ensure_ascii=False))
if __name__=="__main__":
    try:main()
    except (DraftError,ValueError,OSError,KeyError) as exc:
        print("CATEGORY LOOKUP STOPPED",exc,file=sys.stderr)
        sys.exit(1)
