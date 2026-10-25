# Live material-price lookups

The pricebook can search Google Shopping through SerpApi and return offers from multiple merchants (for example, retailers and marketplaces included in the search results). This is a live lookup, not a bulk synchronization: search one selected material at a time, review the matching product, then approve the price. Existing prices are never changed automatically.

## Configure SerpApi

1. Create a SerpApi account and obtain an API key. Check its current plan, request limits, and charges before using it; each material search uses an API request.
2. Set the key in the environment used to launch the app. Do not paste it into the source code, pricebook, or a checked-in file.

Linux/macOS (for the current terminal session):

```sh
export SERPAPI_KEY="your-key"
python3 main.py
```

Windows PowerShell (for the current session):

```powershell
$env:SERPAPI_KEY = "your-key"
python main.py
```

Restart VS Code after setting a persistent environment variable there so the app inherits it. The app uses only Python's standard library for HTTP, so no new package installation is required.

## Use it

- Open **Price book**, select a material, and choose **Find live prices for selected item**. Set the search location (defaults to Maryland, United States).
- In CLI mode, open **Price book**, choose **Update a material price**, then select a returned offer.
- Review the product title, merchant, live listing, and package size. Only apply a price if the product is the correct electrical specification and the listing price is for the pricebook unit. A spool, multi-pack, or bulk listing may not be a per-foot or per-each price.
- The selected merchant, listing title/link, quoted price, location, and lookup time are stored with that material in `data/pricebook.json`.

If a catalog description is too general, add an optional `search_query` field to that material's JSON record with a more specific product/brand/spec search phrase. Offers are search candidates, not guaranteed exact matches, supplier quotes, or installed costs. Availability, account pricing, shipping, and taxes can vary; confirm the listing before using a quote.
