# Broad-catalogue eBay UK selling model — smartvaluestore study

Prepared 22 November 2026 for the interactive eBay sourcing sprint. **Strategy to emulate, not the seller's creative content.** This file is a research note, not a stock purchase, approved listing or publication command.

## Observed operating model

Public seller: https://www.ebay.co.uk/itm/198663715826
- Seller name `smartvaluestore`, UK business seller, displayed 99.1% positive feedback and ~1.1K items sold on profile. Do NOT equate the displayed total with sales per day/month.
- Wide assortment: 3.5mm wired earphones, bamboo kitchen utensils, silicone kitchen sets, car lettering, whiteboard markers, floor wipes, notebooks, etc.
- Keyword-specific fixed-price listings, per-listing variations, multi-buy discounts; some products marked 2 available, 1-business-day dispatch; seller uses several pictures and shipping policies.
- Other listings: bamboo six-piece kitchen utensils £15.16 and 28+ recorded sales (https://www.ebay.co.uk/shop/bamboo-spatula?_nkw=bamboo+spatula); silicone six-piece set £8.89 and 29+ recorded sales (https://www.ebay.co.uk/shop/silicon-kitchen-utensils?_nkw=silicon+kitchen+utensils); whiteboard marker variation listing £2.61, 13 sold but ended 25 October 2026 (https://www.ebay.co.uk/itm/197681994018).
- Cannot infer seller's source, net margins, profit, stock ownership, actual sales velocity or fulfillment methods from listings.

## How to implement responsibly

1. Build a catalogue of many different practical, generic small products; test 1–2 physical units per SKU and then replenish winners; sell as fixed price with optional multi-buy for stock actually on hand.
2. Candidate preflight: exact product/specification and checkout/landed cost, UK seller availability, eBay genuine sold demand rather than merely an asking price, postage thickness and packed weight, business-seller fees, packaging, return allowance, and projected **net profit >= £0.50** per fulfilment (prefer £1–£2).
3. Require exact image provenance / rights. Use own photos of actual inventory or images licensed for resale. No misleading AI mockups purporting to show exact physical stock. Write distinct, accurate descriptions.
4. Avoid live stock greater than physically possessed; when no stock is confirmed, create only zero-stock UNPUBLISHED offers and clearly state the blockers. No duplicate SKUs/offers. Do not automate unverified product publication.
5. UK eBay policy allows wholesale dropshipping with an agreed supplier but prohibits listing and then sourcing from a *retailer* that ships straight to the buyer: https://www.ebay.co.uk/help/selling/shipping-items/setting-shipping-options/dropshipping?id=4176 . Pre-purchased retail inventory held and sent by seller is a different route.
6. Preserve the user's low starter budget (~£50) and Amazon Locker as a sourcing preference where feasible. Spending or supplier ordering needs approval.
7. Existing live eBay listings/stock counts remain unchanged unless user explicitly authorizes targeted revisions.

## Candidate/competitor observations

- 3.5mm wired earphones: £4.94 pictured for seller; UK wholesaler has 24 assorted stereo earphones at £15.36 ex VAT (£18.43 incl VAT at 20%), ~£0.77 inc VAT per pair before inbound shipping: https://www.wholesaledirect.co.uk/buy/wholesale-electrical/wholesale-audio/stereo-wired-earphones_127.htm . However packaged item is 3.5cm thick, likely Small Parcel, so at £4.94 selling price postage+fees may defeat margin; **do not mark viable**. Competing generic wired earbuds also offered below £4.
- Reusable hook-and-loop ties: eBay 100-pack offers below £3, while relevant Amazon 100-packs are generally several pounds more (e.g. £4.99–£7.99). This has sales, but very aggressive price competition; **reject retail sourced 100-pack**. See https://www.ebay.co.uk/shop/hook-and-loop-cable-ties?_nkw=hook+and+loop+cable+ties and https://www.ebay.co.uk/itm/391271150194.
- Silicone spatulas / 6pc utensils: seller recorded sales but packed-size and sourcing costs likely require wholesale to profit. **Research only**, not listed.
- Whiteboard pen bundles: proven modest seller demand but £2.61 asking price likely leaves little room for retail sourcing; **research only**.
- Focus next on compact consumables, stationery and DIY/home accessory bundles that physically fit Royal Mail Large Letter once packaged, with defensible competitive eBay retail price and proven sold volumes.

## Launch checklist per item

| Field | Required verification |
|---|---|
| Product | exact SKU/colour/pack size/brand and physical characteristics |
| Sourcing | actual supplier URL, price incl VAT, delivery terms, stock, pack quantity |
| Fulfilment | owned quantity, packed size and weight, Royal Mail charge, handling time |
| eBay | comparable *sold* demand, competing price, valid UK category, business fees, multi-buy math |
| Profit | sale price minus unit landed cost, eBay fees, outbound postage, packaging, return buffer |
| Media | truthful photos with resale rights and correct details |
| Status | UNPUBLISHED if any verification missing; LIVE only for stock user expressly confirms |
| Proof | eBay listing ID or offer ID, GitHub workflow run log and verification after every change |

Do not publish any candidate on the basis of this research note alone.


## Amazon-only sourcing rule (user direction, 22 Nov 2026)
The buyer has explicitly required **Amazon UK only**, with Locker/Counter collection where eligible. Do not add products sourced from Choice Wholesale or other wholesalers to this Amazon resale workflow. No Amazon-to-eBay retail dropshipping: collect and hold stock before any public listing. Photograph exact owned units, verify sizes/packaging, count them accurately.

### Evidence-led category screening, November 22
- **Cable clips, 20-pack:** eBay competitors at £2.40 for 20 (563 sold) and £3.69 for 20 (1,249 sold): https://www.ebay.co.uk/itm/167383490440 and https://www.ebay.co.uk/itm/277441398177. Amazon product query returned 100 clips for £4.59, or £0.92 per 20 before packing/fees, a likely **reject** at the low eBay selling price. Do not stage until profit confirmed.
- **Mini hair claw clips:** 20 black mini hair claws listed £3.69 and 361 recorded sales; variants at £3.49, 759 recorded sales: https://www.ebay.co.uk/itm/174710928373 and https://www.ebay.co.uk/itm/267284524770. Amazon 50 mini star clips product-search quote £4.99, not exact competitor match. Potential small bundle to test, but postage thickness and exact style/size/colour must be checked. **HOLD**.
- **Kraft gift tags:** 50-pack competitor £2.79 / 86+ recorded sales; highly competitive multivariation https://www.ebay.co.uk/itm/323435516175 with much larger all-time sales. Amazon search result for 200-paper-tag product from £3.79 was not tied to a verified checkout ASIN. **HOLD**, not viable yet.
- **Silicone six-piece kitchen utensils:** eBay examples as low as £3.36/£3.97 for six, with some higher-price variations: https://www.ebay.co.uk/shop/silicon-kitchen-utensil-set?_nkw=silicon+kitchen+utensil+set . Larger size/postage costs suggest retail Amazon sourcing **REJECT** unless exact SKU has documented spread after fees.
- **Earphones:** smartvaluestore listing screenshot showed £4.94, but UK eBay wired earphone competition can be well below £3. Reject unless exact Amazon buy cost, specification and certified safety make a positive margin demonstrable.

### Publication checklist
For each different product, record exact Amazon ASIN URL, exact variant and sellable quantity, current delivered cost and Locker checkout confirmation, eBay *matching* competition/sold evidence, packed weight and dimensions, full postage, eBay fee and VAT where relevant, packaging, reserve, and margin >= £0.50 per sale. Before going live, stock must be purchased/collected and owned, real matching photographs or licensed images available, and business seller policies correct. Stage as an unpublished/stock-zero offer only if user requests staging; no automatic public listing when these conditions are missing.

**Working catalogue goal:** diverse 5–10 compliant products initially, rather than repeatedly listing only craft multipacks. Expand towards 20–50 after actual sales validate economics. No promise of sales or guaranteed profit.
