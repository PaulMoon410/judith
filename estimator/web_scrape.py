"""Best-effort web scraping helpers (stdlib only).

Scraping retailer pages is fragile and may be blocked by anti-bot measures;
these helpers return None on any failure rather than raising.
"""
from __future__ import annotations

import re
import urllib.request
from typing import Optional

_PRICE_RE = re.compile(r"\$\s?(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)")


def fetch_text(url: str, timeout: int = 15) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JudithEstimator/1.0 (contact@example.com)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def first_price(url: str) -> Optional[float]:
    text = fetch_text(url)
    if not text:
        return None
    m = _PRICE_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None
