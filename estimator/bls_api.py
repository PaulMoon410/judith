"""BLS Public Data API helper for electrician wages (stdlib only).

Uses the BLS OEWS series for SOC 47-2111 (Electricians). Series IDs follow the
BLS OEWS layout: OEU{area}000000{soc}{datatype}, where area is the state FIPS
code padded, soc is 472111, and datatype 03 = mean hourly wage.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Optional

# State -> FIPS code
STATE_FIPS = {
    "Alabama": "01", "Alaska": "02", "Arizona": "04", "Arkansas": "05",
    "California": "06", "Colorado": "08", "Connecticut": "09", "Delaware": "10",
    "District of Columbia": "11", "Florida": "12", "Georgia": "13", "Hawaii": "15",
    "Idaho": "16", "Illinois": "17", "Indiana": "18", "Iowa": "19",
    "Kansas": "20", "Kentucky": "21", "Louisiana": "22", "Maine": "23",
    "Maryland": "24", "Massachusetts": "25", "Michigan": "26", "Minnesota": "27",
    "Mississippi": "28", "Missouri": "29", "Montana": "30", "Nebraska": "31",
    "Nevada": "32", "New Hampshire": "33", "New Jersey": "34", "New Mexico": "35",
    "New York": "36", "North Carolina": "37", "North Dakota": "38", "Ohio": "39",
    "Oklahoma": "40", "Oregon": "41", "Pennsylvania": "42", "Rhode Island": "44",
    "South Carolina": "45", "South Dakota": "46", "Tennessee": "47", "Texas": "48",
    "Utah": "49", "Vermont": "50", "Virginia": "51", "Washington": "53",
    "West Virginia": "54", "Wisconsin": "55", "Wyoming": "56",
}

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


def fetch_state_mean_hourly(state: str, start_year: str = "2024",
                           end_year: str = "2025") -> Optional[float]:
    """Return the most recent mean hourly wage for electricians in ``state``.

    Returns None on any failure (network, parse, missing series).
    """
    fips = STATE_FIPS.get(state)
    if not fips:
        return None
    series_id = f"OEU{fips}00000047211103"
    payload = {
        "seriesid": [series_id],
        "startyear": start_year,
        "endyear": end_year,
    }
    try:
        req = urllib.request.Request(
            BLS_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    try:
        series = data["Results"]["series"][0]
        values = series["data"]
        # Most recent first
        values.sort(key=lambda v: (v["year"], v["period"]), reverse=True)
        for v in values:
            if v.get("value") not in (None, ""):
                return float(v["value"])
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return None
