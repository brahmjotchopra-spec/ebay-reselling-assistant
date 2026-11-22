"""Read-only eBay UK category suggestions for researched candidates."""
import urllib.request, urllib.error, urllib.parse, json, sys
from ebay_client import get_token
BASE="https://api.ebay.com/commerce/taxonomy/v1"
terms=["transparent clear school exam pencil case with zip", "pack 12 fridge whiteboard round magnets", "children teacher reward stickers pack", "HB writing pencils with erasers pack of 12"]
def get(path,token):
    req=urllib.request.Request(BASE+path,headers={"Authorization":"Bearer "+token,"Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as exc:
        try:
            j=json.load(exc);errors=[str(x.get("errorId","")) for x in j.get("errors",[])]
        except Exception:errors=[]
        return exc.code,{"errors":errors}
def main():
    t=get_token()
    code,tree=get("/get_default_category_tree_id?marketplace_id=EBAY_GB",t)
    print("Default tree response:",code,"treeId:",tree.get("categoryTreeId"),"errors:",tree.get("errors"))
    if code!=200:sys.exit(1)
    for term in terms:
        url="/category_tree/"+str(tree["categoryTreeId"])+"/get_category_suggestions?q="+urllib.parse.quote(term)
        status,data=get(url,t)
        out=[{"id":x.get("category",{}).get("categoryId"),"name":x.get("category",{}).get("categoryName"),"breadcrumb":[p.get("categoryName") for p in x.get("categoryTreeNodeAncestors",[])]} for x in data.get("categorySuggestions",[])[:6]]
        print("Query:",term,"HTTP:",status,"candidates:",json.dumps(out,ensure_ascii=False),"errors:",data.get("errors",[]))
if __name__=="__main__":main()
