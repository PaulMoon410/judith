"""Google Shopping price lookups through SerpApi (API key supplied by environment)."""
from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://serpapi.com/search.json"


class PriceLookupError(RuntimeError):
    """Raised when a live material-price lookup cannot be completed."""


def search_material_prices(query: str, location: str = "Maryland, United States") -> list[dict]:
    """Return Google Shopping offers from multiple merchants for ``query``.

    This only discovers candidate listings. The caller must verify the exact
    product and package/unit price before applying an offer to the pricebook.
    """
    api_key = os.environ.get("SERPAPI_KEY", "").strip()
    if not api_key:
        raise PriceLookupError(
            "SERPAPI_KEY is not set. Follow docs/material_price_api.md to configure it."
        )
    if not query.strip():
        raise PriceLookupError("Enter a material name to search for.")

    params = urlencode({
        "engine": "google_shopping",
        "q": query.strip(),
        "location": location.strip() or "Maryland, United States",
        "gl": "us",
        "hl": "en",
        "api_key": api_key,
    })
    request = Request(f"{API_URL}?{params}", headers={"User-Agent": "EstimatorApp/1.0"})
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise PriceLookupError(f"Price provider returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise PriceLookupError(f"Could not reach the price provider: {exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PriceLookupError("The price provider returned an unreadable response.") from exc

    if payload.get("error"):
        raise PriceLookupError(str(payload["error"]))

    offers = []
    for item in payload.get("shopping_results", []):
        price_value = item.get("extracted_price")
        if price_value is None:
            raw_price = str(item.get("price", ""))
            match = re.search(r"\d[\d,]*(?:\.\d{1,2})?", raw_price)
            price_value = float(match.group(0).replace(",", "")) if match else None
        try:
            price = float(price_value)
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        offers.append({
            "title": str(item.get("title", "Untitled product")),
            "source": str(item.get("source", "Unknown merchant")),
            "price": round(price, 2),
            "url": str(item.get("product_link") or item.get("link") or ""),
        })
    return offers[:10]
