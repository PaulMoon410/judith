"""Multi-source labor rate engine (stdlib only).

The estimator needs a defensible labor $/hour instead of one hardcoded number.
This module aggregates several independent public sources, converts them to a
common basis, and produces a recommended billable rate per state.

Sources modelled
----------------
* ``bls_wage``        -- U.S. Bureau of Labor Statistics OEWS mean/median wage
                         for Electricians (SOC 47-2111). This is a *wage* (what
                         the electrician is paid), not a billable rate.
* ``neca_billing``    -- National Electrical Contractors Association style
                         contractor billing rates, as reported in industry
                         pricing guides.
* ``contractor_survey`` -- Published contractor rate surveys (e.g. Housecall
                         Pro, Angi, HomeAdvisor aggregated ranges).
* ``retail_billing``  -- Consumer-facing "what electricians charge" cost guides.

Converting wage -> billable rate
--------------------------------
Wage figures cannot be billed directly. A contractor must recover payroll
taxes, workers' comp, general liability, vehicles, tools, non-billable time
and profit. We apply a *burden multiplier* plus an *overhead & profit* layer:

    billable = wage * burden_multiplier * (1 + overhead_profit_pct)

The defaults below are the common convention in electrical estimating
(1.35-1.65 burden; 25-40% overhead & profit). Every value here is a *planning
benchmark*, not a quote -- always confirm against your own payroll and market.

Nothing in this module guesses silently: every number carries its source and
the derivation is shown so the user can accept or override it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --- Tunable conversion assumptions -----------------------------------------

# Payroll taxes, workers' comp, general liability, paid time off and typical
# non-billable time expressed as a multiplier on the raw wage.
DEFAULT_BURDEN_MULTIPLIER = 1.45

# Overhead (trucks, tools, insurance, office) plus target profit, applied on
# top of the burdened labor cost. Contractors commonly run 25-40%.
DEFAULT_OVERHEAD_PROFIT_PCT = 32.0

# Billable hours actually sold out of a paid year. Used only for documentation;
# the multiplier above already folds in non-billable time.
DEFAULT_BILLABLE_HOURS_PER_YEAR = 1450


@dataclass
class RateSource:
    """One independent source of labor rate data."""

    key: str
    label: str
    kind: str  # "wage" (paid to electrician) or "billing" (charged to customer)
    low: float
    typical: float
    high: float
    as_of: str
    url: str
    note: str = ""

    def as_billable(self, burden: float = DEFAULT_BURDEN_MULTIPLIER,
                    overhead_pct: float = DEFAULT_OVERHEAD_PROFIT_PCT) -> "RateSource":
        """Return this source expressed as a customer-facing billable rate.

        Wage-basis sources are scaled by the burden multiplier and overhead;
        billing-basis sources are already customer-facing and pass through.
        """
        if self.kind != "wage":
            return self
        factor = burden * (1 + overhead_pct / 100.0)
        return RateSource(
            key=self.key,
            label=f"{self.label} (burdened)",
            kind="billing",
            low=round(self.low * factor, 2),
            typical=round(self.typical * factor, 2),
            high=round(self.high * factor, 2),
            as_of=self.as_of,
            url=self.url,
            note=self.note,
        )


# --- National source data ----------------------------------------------------
# BLS figure is the May 2024 OEWS mean for Electricians ($29.98/hr, $62,350/yr).
# Billing ranges come from published contractor pricing guides (2025-2026).

NATIONAL_SOURCES: tuple[RateSource, ...] = (
    RateSource(
        key="bls_wage",
        label="BLS OEWS wage (Electricians, SOC 47-2111)",
        kind="wage",
        low=18.00,       # ~10th percentile
        typical=29.98,   # national mean, May 2024
        high=48.00,      # ~90th percentile
        as_of="May 2024",
        url="https://www.bls.gov/ooh/construction-and-extraction/electricians.htm",
        note="Wage paid to the electrician; must be burdened to bill.",
    ),
    RateSource(
        key="contractor_survey",
        label="Contractor rate survey (Housecall Pro)",
        kind="billing",
        low=40.00,
        typical=70.00,
        high=100.00,
        as_of="2026",
        url="https://www.housecallpro.com/resources/how-to-price-electrical-work/",
        note="Journeyman ~$38/hr wage; master $90-100+/hr; $100-200 service call.",
    ),
    RateSource(
        key="retail_billing",
        label="Consumer cost guide (latestcost / HomeAdvisor)",
        kind="billing",
        low=50.00,
        typical=75.00,
        high=120.00,
        as_of="2026",
        url="https://latestcost.com/electrician-cost-per-hour-united-states/",
        note="Typical residential billing range, normal business hours.",
    ),
)


# --- State wage adjustment ---------------------------------------------------
# Ratio of state electrician mean wage to the national mean. Values are rounded
# planning indices derived from BLS state wage tables; 1.00 means "national
# average". States not listed fall back to 1.00. These adjust the *wage* basis
# only, then the same burden/overhead conversion is applied.
STATE_WAGE_INDEX: dict[str, float] = {
    "Alabama": 0.88, "Alaska": 1.22, "Arizona": 0.98, "Arkansas": 0.88,
    "California": 1.28, "Colorado": 1.05, "Connecticut": 1.20, "Delaware": 1.02,
    "District of Columbia": 1.30, "Florida": 0.94, "Georgia": 0.94, "Hawaii": 1.18,
    "Idaho": 0.92, "Illinois": 1.12, "Indiana": 0.95, "Iowa": 0.94, "Kansas": 0.94,
    "Kentucky": 0.90, "Louisiana": 0.92, "Maine": 1.00, "Maryland": 1.10,
    "Massachusetts": 1.24, "Michigan": 1.02, "Minnesota": 1.10, "Mississippi": 0.86,
    "Missouri": 0.94, "Montana": 0.92, "Nebraska": 0.94, "Nevada": 0.98,
    "New Hampshire": 1.08, "New Jersey": 1.20, "New Mexico": 0.92, "New York": 1.22,
    "North Carolina": 0.94, "North Dakota": 0.98, "Ohio": 0.98, "Oklahoma": 0.90,
    "Oregon": 1.12, "Pennsylvania": 1.08, "Rhode Island": 1.12,
    "South Carolina": 0.92, "South Dakota": 0.90, "Tennessee": 0.92, "Texas": 0.98,
    "Utah": 0.96, "Vermont": 1.02, "Virginia": 1.06, "Washington": 1.20,
    "West Virginia": 0.88, "Wisconsin": 1.02, "Wyoming": 0.94,
}


def state_wage_index(state: str) -> float:
    return STATE_WAGE_INDEX.get(state, 1.00)


@dataclass
class RateComparison:
    """The full multi-source comparison and its recommended value."""

    state: str
    burden_multiplier: float
    overhead_profit_pct: float
    sources: list[RateSource] = field(default_factory=list)

    @property
    def billable_sources(self) -> list[RateSource]:
        return [s.as_billable(self.burden_multiplier, self.overhead_profit_pct) for s in self.sources]

    @property
    def typical(self) -> float:
        """Median of the sources' typical values (billable basis)."""
        vals = sorted(s.typical for s in self.billable_sources)
        return round(_median(vals), 2)

    @property
    def low(self) -> float:
        return round(min(s.low for s in self.billable_sources), 2)

    @property
    def high(self) -> float:
        return round(max(s.high for s in self.billable_sources), 2)

    @property
    def recommended(self) -> float:
        """Blended recommendation, rounded to the nearest dollar."""
        return float(round(self.typical))


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2.0


def compare_rates(state: str = "Maryland",
                  burden: float = DEFAULT_BURDEN_MULTIPLIER,
                  overhead_pct: float = DEFAULT_OVERHEAD_PROFIT_PCT,
                  custom_sources: list[dict] | None = None) -> RateComparison:
    """Build a multi-source comparison for ``state``.

    ``custom_sources`` lets a saved pricebook supply refreshed or user-added
    sources. A custom source whose ``key`` matches a built-in *replaces* it
    (so refreshed figures do not double-count); a new key is appended.
    """
    idx = state_wage_index(state)
    custom_by_key: dict[str, RateSource] = {}
    for cs in custom_sources or []:
        try:
            custom_by_key[str(cs["key"])] = RateSource(
                key=cs["key"],
                label=cs["label"],
                kind=cs.get("kind", "billing"),
                low=float(cs["low"]),
                typical=float(cs["typical"]),
                high=float(cs["high"]),
                as_of=str(cs.get("as_of", "")),
                url=str(cs.get("url", "")),
                note=str(cs.get("note", "")),
            )
        except (KeyError, TypeError, ValueError):
            continue

    sources: list[RateSource] = []
    used_keys: set[str] = set()
    for s in NATIONAL_SOURCES:
        used_keys.add(s.key)
        base = custom_by_key.get(s.key, s)
        if base.kind == "wage":
            sources.append(
                RateSource(
                    key=base.key,
                    label=f"{base.label} - {state} index {idx:.2f}",
                    kind="wage",
                    low=round(base.low * idx, 2),
                    typical=round(base.typical * idx, 2),
                    high=round(base.high * idx, 2),
                    as_of=base.as_of,
                    url=base.url,
                    note=base.note,
                )
            )
        else:
            sources.append(base)

    # Append custom sources that do not override a built-in.
    for key, cs in custom_by_key.items():
        if key not in used_keys:
            sources.append(cs)

    return RateComparison(state=state, burden_multiplier=burden, overhead_profit_pct=overhead_pct, sources=sources)


def format_report(cmp: RateComparison) -> str:
    """Plain-text report comparing sources and the recommendation."""
    lines = [
        f"Labor rate comparison - {cmp.state}",
        f"Burden multiplier: {cmp.burden_multiplier:.2f}   "
        f"Overhead & profit: {cmp.overhead_profit_pct:.0f}%",
        "Wage sources are converted to a billable rate with the factors above.",
        "-" * 78,
        f"{'Source':<44}{'Low':>10}{'Typical':>10}{'High':>10}",
        "-" * 78,
    ]
    for s in cmp.billable_sources:
        lines.append(f"{s.label[:43]:<44}{s.low:>10.2f}{s.typical:>10.2f}{s.high:>10.2f}")
    lines.append("-" * 78)
    lines.append(f"{'Blended (median of typical)':<44}{cmp.low:>10.2f}{cmp.typical:>10.2f}{cmp.high:>10.2f}")
    lines.append("")
    lines.append(f"Recommended labor rate: ${cmp.recommended:.2f}/hr")
    lines.append("")
    lines.append("Sources:")
    for s in cmp.sources:
        lines.append(f"  - {s.label} ({s.as_of}) [{s.kind}]: {s.url}")
        if s.note:
            lines.append(f"      {s.note}")
    lines.append("")
    lines.append("These are planning benchmarks, not a quote. Confirm against your")
    lines.append("own payroll, burden, and local market before bidding.")
    return "\n".join(lines)


def refresh_bls_source(state: str = "Maryland") -> dict | None:
    """Fetch a live BLS wage figure and return it as a custom source dict."""
    from . import bls_api

    wage = bls_api.fetch_state_mean_hourly(state)
    if wage is None:
        return None
    return {
        "key": "bls_wage",
        "label": f"BLS OEWS wage (Electricians) - {state} (live)",
        "kind": "wage",
        "low": round(wage * 0.6, 2),
        "typical": round(wage, 2),
        "high": round(wage * 1.6, 2),
        "as_of": "live",
        "url": "https://www.bls.gov/oes/",
        "note": "Live fetch from BLS Public Data API (SOC 47-2111).",
    }
