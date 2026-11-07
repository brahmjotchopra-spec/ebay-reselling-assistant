# ebay-reselling-assistant

Prepare fixed-price UK eBay drafts for commercially reviewed products. The default command is offline. It validates the private product file and reports how many rows are eligible.

```sh
python3 -m unittest discover -s tests -v
python3 ebay_bot.py --file private/products.json
python3 ebay_bot.py --file private/products.json --seller-hub-csv private/uk-drafts.csv
```

Use Python 3.10 or later. The tool uses only the standard library. The CSV is an eBay UK Seller Hub **Create drafts** file. Upload it once in Seller Hub → Reports → Upload, then check the upload result and open Listings → Drafts. Every row has action `Draft`. Quantity stays blank. Re-uploading the same CSV can create additional drafts.

## Account access

Use a production **seller** OAuth grant with `https://api.ebay.com/oauth/api_scope/sell.inventory`. Keep credential values in the local environment or in GitHub Actions secrets on the repository running the workflow.

| Variable | Purpose |
| --- | --- |
| `EBAY_CLIENT_ID` | Production App ID |
| `EBAY_CLIENT_SECRET` | Production Cert ID |
| `EBAY_REFRESH_TOKEN` | Seller refresh token issued to that application |
| `EBAY_ACCESS_TOKEN` | Short-lived seller access token, usable in place of the three renewable credentials |
| `EBAY_LISTINGS_JSON` | Optional private product array for Actions |

```sh
python3 ebay_bot.py --check-credentials
python3 ebay_bot.py --file private/products.json --create-unpublished
```

The first command reports which names are set, then tries a read from the production Inventory API. A successful read with a short-lived token establishes read access. The second command runs the commercial checks and creates an inventory item and an unpublished UK offer only for eligible rows. It reads the offer back to verify its ID and unpublished status.

Use one draft route per product. Inventory API offers are reviewed by offer ID. The Seller Hub CSV route creates native Seller Hub drafts. Reserve the `DRAFT-` SKU prefix for this tool. Runs reuse matching records after interruptions and stop on conflicts. Both inventory and offer quantity are zero.

## Commercial review file

The checked-in `listings.json` is empty. Save the real array under `private/`, or use the manifest secret for GitHub Actions. Each row needs a unique supplier SKU, a title, description, eBay condition, UK category ID and GBP price. `aspects`, `image_urls` and `ean` are optional. Use images supplied for reseller use. This example stays on hold until the operator records a real review and approves the row.

```json
[
  {
    "sku": "EXAMPLE-1",
    "title": "Example product",
    "description": "Replace with verified product details.",
    "condition": "NEW",
    "category_id": "262204",
    "price_gbp": "11.79",
    "approved_for_unpublished_offer": false,
    "commercial_review": {
      "verified": false,
      "checked_on": "",
      "stock": 0,
      "supplier_url": "",
      "demand_url": "",
      "delivery_terms": "",
      "wholesale_inc_vat": "0.00",
      "delivery_inc_vat": "0.00",
      "supplier_payment_fee": "0.00",
      "ebay_percent": "9.85",
      "fee_vat_percent": "20",
      "per_order_ex_vat": "0.40",
      "insertion_ex_vat": "0.30",
      "reserve_gbp": "0.59"
    }
  }
]
```

Record the verified unit cost, delivery charge and evidence for that seller, SKU and delivery area. Use the current London date (`YYYY-MM-DD`). `ebay_percent` includes the final-value and regulatory fees. The calculation deducts supplier costs, eBay fees including VAT, and the stated reserve from the selling price. It requires at least £3.50 per unit and checks that one fulfilment for every eligible SKU fits together within £50. It never commits that money. Review delivery exclusions and seller policies separately before any later decision to publish.

## GitHub Actions

On `main`, a change to the workflow or either application module runs tests and the read-only credential check. Under **Actions → eBay UK drafts → Run workflow**, choose `preview`, `credentials`, or `create-unpublished`. Only the last manual option writes offers. The workflow uses a standard runner, serialises runs and keeps seller records and offer IDs out of public logs. There is no publication, payment or supplier order operation.

[Seller Hub Reports](https://www.ebay.co.uk/help/selling/selling-tools/reports?id=4096) · [eBay OAuth](https://developer.ebay.com/develop/guides/sell/authorization) · [Managing eBay offers](https://developer.ebay.com/api-docs/sell/static/inventory/managing-offers.html)
