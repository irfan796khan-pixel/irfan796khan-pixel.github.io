"""Refresh catalog/live.js from the public Mayflower Shopify store.

Reads mayflowerwholesale.com/products.json (public, no password) and writes, for every
Shopify variant used on the catalog page: [price, available].
A variant that is no longer on the online store is simply left out; the page shows it as sold out.
Only selling prices are read. No cost data exists in this feed.
"""
import json, re, sys, time, urllib.request, datetime, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ITEMS = ROOT / "catalog" / "items.js"
OUT = ROOT / "catalog" / "live.js"
SHOP = "https://mayflowerwholesale.com/products.json?limit=250&page={}"

wanted = set(re.findall(r'(?<![-\d])(\d{14})(?=[,\]])', ITEMS.read_text(encoding="utf-8")))

seen, page = {}, 1
while True:
    req = urllib.request.Request(SHOP.format(page), headers={"User-Agent": "mayflower-catalog-refresh"})
    for attempt in range(3):
        try:
            data = json.load(urllib.request.urlopen(req, timeout=60))
            break
        except Exception as e:
            if attempt == 2:
                sys.exit(f"Shopify read failed on page {page}: {e}")   # keep the old live.js
            time.sleep(10)
    products = data.get("products", [])
    for p in products:
        for v in p.get("variants", []):
            seen[str(v["id"])] = [round(float(v["price"]), 2), 1 if v.get("available") else 0]
    if len(products) < 250:
        break
    page += 1

if len(seen) < 100:   # safety: a near-empty answer is a Shopify hiccup, not a real catalog
    sys.exit(f"Only {len(seen)} variants came back; not overwriting live.js")

live = {k: seen[k] for k in sorted(wanted) if k in seen}
now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")
OUT.write_text(
    "/* Written automatically from mayflowerwholesale.com. variantId -> [price, available].\n"
    "   Missing id = not on the online store = shown as sold out. */\n"
    f"window.LIVE_AT = {json.dumps(now)};\n"
    f"window.LIVE = {json.dumps(live, separators=(',', ':'))};\n",
    encoding="utf-8")
print(f"{len(live)} of {len(wanted)} catalog variants are on the store; "
      f"{sum(1 for v in live.values() if not v[1])} unavailable; {len(wanted) - len(live)} not on the store")
