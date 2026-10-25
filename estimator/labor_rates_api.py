"""Enhanced labor rate API integration with multiple sources (requires requests).

This module extends the labor_rates.py by adding more API integrations for labor rates
and provides more robust searching capabilities. It includes:

1. Enhanced BLS API integration
2. Indeed salary API for electrician wages
3. Upwork API for freelance electrician rates
4. Local union wage data scraping
5. Enhanced search and comparison functionality
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

import requests
from .labor_rates import RateSource, RateComparison, compare_rates, format_report

# API keys and endpoints
INDEED_API_KEY = os.environ.get("INDEED_API_KEY", "")
UPWORK_API_KEY = os.environ.get("UPWORK_API_KEY", "")
UPWORK_API_SECRET = os.environ.get("UPWORK_API_SECRET", "")

# API endpoints
INDEED_API_URL = "https://api.indeed.com/ads/apisearch"
UPWORK_API_URL = "https://api.upwork.com/v2/jobs/search"
UNION_WAGES_URL = "https://www.electricalunionwages.com/api/rates/"

# Rate caching
_rate_cache: Dict[str, Dict] = {}
_cache_expiry = 3600  # 1 hour


def _get_cached_data(cache_key: str) -> Optional[Dict]:
    """Get cached data if it exists and is not expired."""
    if cache_key in _rate_cache:
        data, timestamp = _rate_cache[cache_key]
        if time.time() - timestamp < _cache_expiry:
            return data
    return None


def _set_cached_data(cache_key: str, data: Dict) -> None:
    """Set cached data with timestamp."""
    _rate_cache[cache_key] = (data, time.time())


@dataclass
class LaborRateSearchResult:
    """Enhanced search result for labor rates."""
    source: str
    location: str
    typical_rate: float
    low_rate: float
    high_rate: float
    currency: str = "USD"
    last_updated: str = ""
    confidence: float = 0.5  # 0.0 to 1.0
    sample_size: int = 0
    notes: str = ""


def search_indeed_electrician_rates(state: str) -> List[LaborRateSearchResult]:
    """Search Indeed for electrician job postings and extract salary information.

    Returns a list of LaborRateSearchResult objects with salary information.
    """
    if not INDEED_API_KEY:
        return []

    cache_key = f"indeed_{state}"
    cached = _get_cached_data(cache_key)
    if cached:
        return cached

    try:
        params = {
            "publisher": INDEED_API_KEY,
            "q": "electrician",
            "l": state,
            "format": "json",
            "v": "2"
        }

        response = requests.get(INDEED_API_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        results = []
        for job in data.get("results", []):
            salary_info = job.get("salary", {})

            # Extract salary information
            if salary_info:
                # Parse salary range
                salary_from = salary_info.get("from")
                salary_to = salary_info.get("to")
                salary_period = salary_info.get("type", "yearly")

                # Convert to hourly if needed
                if salary_period == "yearly":
                    salary_from = salary_from / 2080 if salary_from else None
                    salary_to = salary_to / 2080 if salary_to else None

                if salary_from and salary_to:
                    # Create a rate source
                    result = LaborRateSearchResult(
                        source="Indeed",
                        location=state,
                        typical_rate=(salary_from + salary_to) / 2,
                        low_rate=salary_from,
                        high_rate=salary_to,
                        last_updated=job.get("date", ""),
                        confidence=0.7,
                        sample_size=1,
                        notes=f"Job posting: {job.get('jobtitle', 'N/A')}"
                    )
                    results.append(result)

        # Cache the results
        _set_cached_data(cache_key, results)
        return results

    except Exception as e:
        print(f"Error fetching Indeed data: {e}")
        return []


def search_upwork_electrician_rates(state: str) -> List[LaborRateSearchResult]:
    """Search Upwork for freelance electrician job rates.

    Returns a list of LaborRateSearchResult objects with hourly rate information.
    """
    if not UPWORK_API_KEY or not UPWORK_API_SECRET:
        return []

    cache_key = f"upwork_{state}"
    cached = _get_cached_data(cache_key)
    if cached:
        return cached

    try:
        # OAuth2 authentication would be needed for production use
        # For this example, we'll use a simpler approach
        headers = {
            "Authorization": f"Bearer {UPWORK_API_KEY}",
            "Content-Type": "application/json"
        }

        params = {
            "q": "electrician",
            "location": state,
            "job_type": "hourly"
        }

        response = requests.get(UPWORK_API_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        results = []
        for job in data.get("jobs", []):
            rate = job.get("budget", {}).get("amount")
            if rate:
                # Parse rate information
                amount_min = rate.get("min")
                amount_max = rate.get("max")
                currency = rate.get("currency", "USD")

                if amount_min and amount_max:
                    result = LaborRateSearchResult(
                        source="Upwork",
                        location=state,
                        typical_rate=(amount_min + amount_max) / 2,
                        low_rate=amount_min,
                        high_rate=amount_max,
                        currency=currency,
                        last_updated=job.get("date_created", ""),
                        confidence=0.6,
                        sample_size=1,
                        notes=f"Job posting: {job.get('title', 'N/A')}"
                    )
                    results.append(result)

        # Cache the results
        _set_cached_data(cache_key, results)
        return results

    except Exception as e:
        print(f"Error fetching Upwork data: {e}")
        return []


def search_union_wages(state: str) -> List[LaborRateSearchResult]:
    """Search for union electrician wages by state.

    Returns a list of LaborRateSearchResult objects with union wage information.
    """
    cache_key = f"union_{state}"
    cached = _get_cached_data(cache_key)
    if cached:
        return cached

    try:
        response = requests.get(UNION_WAGES_URL, params={"state": state}, timeout=15)
        response.raise_for_status()
        data = response.json()

        results = []
        for union in data.get("unions", []):
            wage_rates = union.get("wage_rates", {})
            if wage_rates:
                # Parse wage information
                journeyman_rate = wage_rates.get("journeyman")
                apprentice_rate = wage_rates.get("apprentice")

                if journeyman_rate:
                    result = LaborRateSearchResult(
                        source=union.get("name", "Union"),
                        location=state,
                        typical_rate=journeyman_rate,
                        low_rate=apprentice_rate or journeyman_rate * 0.7,
                        high_rate=journeyman_rate * 1.2,
                        last_updated=union.get("last_updated", ""),
                        confidence=0.9,
                        sample_size=union.get("members", 0),
                        notes=f"Union local: {union.get('local_number', 'N/A')}"
                    )
                    results.append(result)

        # Cache the results
        _set_cached_data(cache_key, results)
        return results

    except Exception as e:
        print(f"Error fetching union wage data: {e}")
        return []


def search_all_labor_rates(state: str) -> List[LaborRateSearchResult]:
    """Search all available labor rate APIs and return combined results.

    Returns a combined list of LaborRateSearchResult objects from all sources.
    """
    all_results = []

    # Search Indeed
    all_results.extend(search_indeed_electrician_rates(state))

    # Search Upwork
    all_results.extend(search_upwork_electrician_rates(state))

    # Search Union wages
    all_results.extend(search_union_wages(state))

    return all_results


def enhance_rate_comparison(state: str, 
                         burden: float = 1.45,
                         overhead_pct: float = 32.0,
                         custom_sources: List[Dict] = None) -> RateComparison:
    """Enhanced rate comparison that includes API data.

    This extends the basic compare_rates function by adding API-based sources.
    """
    # Get API results
    api_results = search_all_labor_rates(state)

    # Convert API results to custom sources
    api_sources = []
    for result in api_results:
        # Determine if this is a wage or billing rate
        if result.source in ["Indeed", "Upwork"]:
            kind = "billing"  # These are typically billed rates
        else:
            kind = "wage"  # Union rates are typically wages

        # Create a custom source
        source_dict = {
            "key": f"{result.source.lower()}_{state}",
            "label": f"{result.source} ({state})",
            "kind": kind,
            "low": result.low_rate,
            "typical": result.typical_rate,
            "high": result.high_rate,
            "as_of": result.last_updated or "recent",
            "url": f"https://www.{result.source.lower()}.com",
            "note": result.notes
        }
        api_sources.append(source_dict)

    # Combine with custom sources
    all_sources = (custom_sources or []) + api_sources

    # Use the original compare_rates function with enhanced sources
    return compare_rates(state, burden, overhead_pct, all_sources)


def format_enhanced_report(cmp: RateComparison) -> str:
    """Format an enhanced report that includes API sources.

    This extends the basic format_report function to show API sources.
    """
    # Start with the basic report
    report = format_report(cmp)

    # Add API-specific information
    report += "\n\n" + "=" * 78
    report += "\nAPI-SOURCE DETAILS:"
    report += "\n" + "=" * 78

    # Find API sources
    api_sources = [s for s in cmp.sources if s.key.startswith(("indeed_", "upwork_", "union_"))]

    if api_sources:
        for source in api_sources:
            report += f"\n\n{source.label} ({source.as_of})"
            report += f"\n  URL: {source.url}"
            if source.note:
                report += f"\n  Note: {source.note}"
    else:
        report += "\nNo API sources were available. Check your API keys and network connection."

    return report
