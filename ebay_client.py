"""Production eBay UK Inventory API calls used by the draft tool."""

import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


API_ROOT = "https://api.ebay.com"
INVENTORY = API_ROOT + "/sell/inventory/v1"
SCOPE = "https://api.ebay.com/oauth/api_scope/sell.inventory"
REFRESH_KEYS = ("EBAY_CLIENT_ID", "EBAY_CLIENT_SECRET", "EBAY_REFRESH_TOKEN")
ACCESS_KEY = "EBAY_ACCESS_TOKEN"


class DraftError(Exception):
    pass


class ApiError(DraftError):
    def __init__(self, status, ids):
        self.status = status
        self.ids = set(ids)
        codes = ", ".join(map(str, sorted(self.ids))) or "no error ID"
        super().__init__(f"eBay returned HTTP {status} ({codes}).")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def request_json(request):
    try:
        with build_opener(NoRedirect()).open(request, timeout=25) as response:
            body = response.read()
    except HTTPError as exc:
        try:
            errors = json.loads(exc.read()).get("errors", [])
            ids = [e["errorId"] for e in errors if isinstance(e, dict) and
                   isinstance(e.get("errorId"), int)]
        except (ValueError, TypeError, AttributeError):
            ids = []
        raise ApiError(exc.code, ids) from None
    except (URLError, OSError) as exc:
        raise DraftError("Could not reach eBay. Rerun to reconcile the server state.") from None
    try:
        result = json.loads(body) if body.strip() else {}
    except ValueError:
        raise DraftError("eBay returned an unreadable response.") from None
    if not isinstance(result, dict):
        raise DraftError("Unexpected eBay response.")
    return result


def get_token():
    keys = [os.environ.get(key, "").strip() for key in REFRESH_KEYS]
    if all(keys):
        client_id, secret, refresh = keys
        basic = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
        form = urlencode({"grant_type": "refresh_token", "refresh_token": refresh,
                          "scope": SCOPE}).encode()
        req = Request(API_ROOT + "/identity/v1/oauth2/token", data=form, method="POST",
                      headers={"Authorization": "Basic " + basic,
                               "Content-Type": "application/x-www-form-urlencoded"})
        token = request_json(req).get("access_token")
        if not isinstance(token, str) or not token.strip():
            raise DraftError("eBay did not issue a seller access token.")
        return token
    token = os.environ.get(ACCESS_KEY, "").strip()
    if token:
        return token
    missing = ", ".join(k for k, v in zip(REFRESH_KEYS, keys) if not v)
    raise DraftError(f"No seller token. Missing renewable credentials: {missing}.")


class Inventory:
    def __init__(self, token):
        self.headers = {"Authorization": "Bearer " + token, "Content-Language": "en-GB",
                        "Content-Type": "application/json", "Accept": "application/json"}

    def _request(self, method, path, payload=None):
        body = json.dumps(payload).encode() if payload is not None else None
        return request_json(Request(INVENTORY + path, data=body, method=method,
                                    headers=self.headers))

    def check_access(self):
        self._request("GET", "/inventory_item?limit=1")

    def item(self, sku):
        try:
            return self._request("GET", "/inventory_item/" + quote(sku, safe=""))
        except ApiError as exc:
            if self._absent(exc, {25702, 25710}):
                return None
            raise

    @staticmethod
    def _absent(exc, allowed):
        return (exc.status in (400, 404) and bool(exc.ids) and exc.ids <= allowed)

    def offers(self, sku):
        try:
            data = self._request("GET", "/offer?" + urlencode({"sku": sku}))
        except ApiError as exc:
            if self._absent(exc, {25702, 25710, 25713}):
                return []
            raise
        offers = data.get("offers", [] if data.get("total") == 0 else None)
        if not isinstance(offers, list) or data.get("next") or data.get("total", len(offers)) != len(offers):
            raise DraftError("Cannot establish the complete offer state for this SKU.")
        return offers

    def create_item(self, sku, data):
        self._request("PUT", "/inventory_item/" + quote(sku, safe=""), data)

    def create_offer(self, data):
        response = self._request("POST", "/offer", data)
        offer_id = response.get("offerId")
        if not isinstance(offer_id, str) or not offer_id:
            raise DraftError("Offer creation returned no ID. Rerun to reconcile.")
        return offer_id

    def offer(self, offer_id):
        return self._request("GET", "/offer/" + quote(offer_id, safe=""))
