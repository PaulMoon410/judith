"""Quick-reference NEC residential load calculator (standard method, NEC 220).

This computes the MINIMUM general lighting/receptacle requirements for a
dwelling unit based on square footage:
  - General lighting load: NEC Table 220.12 -> 3 VA per sq ft (dwelling unit)
  - Small appliance circuits: NEC 220.52(A) -> at least 2 circuits, 1500 VA each
  - Laundry circuit: NEC 220.52(B) -> at least 1 circuit, 1500 VA
  - Bathroom circuit: NEC 210.11(C)(3) -> at least 1 dedicated 20A circuit
  - Demand factors: NEC Table 220.42 applied to the combined general
    lighting + small appliance + laundry load.

This is a simplified reference for BASE minimums only. It does NOT include
fixed appliances, HVAC, ranges, dryers, EVSE, or other dwelling loads, and is
not a substitute for a full NEC 220 calculation, a licensed electrician, or
your local AHJ's plan review.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

GENERAL_LIGHTING_VA_PER_SQFT = 3

OCCUPANCY_LIGHTING_VA = {
    "armories_auditoriums": {"2017": 1.0, "2020": 1.0, "2023": 1.0},
    "banks": {"2017": 3.5, "2020": 1.3, "2023": 1.3},
    "barber_beauty": {"2017": 3.0, "2020": 3.0, "2023": 3.0},
    "churches": {"2017": 1.0, "2020": 1.0, "2023": 1.0},
    "clubs": {"2017": 2.0, "2020": 2.0, "2023": 2.0},
    "court_houses": {"2017": 2.0, "2020": 1.4, "2023": 1.4},
    "dwelling": {"2017": 3.0, "2020": 3.0, "2023": 3.0},
    "garages_commercial": {"2017": 0.5, "2020": 0.5, "2023": 0.5},
    "hospitals": {"2017": 2.0, "2020": 1.6, "2023": 1.6},
    "hotels_motels": {"2017": 2.0, "2020": 2.0, "2023": 2.0},
    "industrial": {"2017": 2.0, "2020": 2.0, "2023": 1.6},
    "lodge_rooms": {"2017": 1.5, "2020": 1.5, "2023": 1.5},
    "office": {"2017": 3.5, "2020": 1.3, "2023": 1.3},
    "restaurants": {"2017": 2.0, "2020": 2.0, "2023": 2.0},
    "schools": {"2017": 3.0, "2020": 1.3, "2023": 1.3},
    "stores": {"2017": 3.0, "2020": 3.0, "2023": 1.9},
    "warehouses": {"2017": 0.25, "2020": 0.1, "2023": 0.1},
}


def occupancy_lighting_va(occupancy: str, year: str = "2023") -> float:
    return OCCUPANCY_LIGHTING_VA.get(occupancy, {}).get(year, 0.0)
SMALL_APPLIANCE_CIRCUITS_MIN = 2
SMALL_APPLIANCE_VA_EACH = 1500
LAUNDRY_CIRCUIT_VA = 1500
BATHROOM_CIRCUITS_MIN = 1


@dataclass
class NecResult:
    square_feet: float
    circuit_amps: float
    service_voltage: float
    general_lighting_va: float
    small_appliance_va: float
    laundry_va: float
    gross_va: float
    demand_va: float
    min_service_amps: float
    min_lighting_circuits: int
    min_small_appliance_circuits: int
    min_laundry_circuits: int
    min_bathroom_circuits: int


def _apply_standard_demand_factors(gross_va: float) -> float:
    """NEC Table 220.42: first 3000 VA @ 100%, next up to 120,000 VA @ 35%, remainder @ 25%."""
    if gross_va <= 3000:
        return gross_va
    remainder = gross_va - 3000
    tier_35 = min(remainder, 117000)
    demand = 3000 + tier_35 * 0.35
    if remainder > 117000:
        demand += (remainder - 117000) * 0.25
    return demand


def calculate(square_feet: float, circuit_amps: float = 20, service_voltage: float = 240) -> NecResult:
    if square_feet <= 0:
        raise ValueError("Square footage must be greater than zero.")
    if circuit_amps not in (15, 20):
        raise ValueError("General lighting circuit size must be 15A or 20A.")
    if service_voltage <= 0:
        raise ValueError("Service voltage must be greater than zero.")
    general_lighting_va = square_feet * GENERAL_LIGHTING_VA_PER_SQFT
    small_appliance_va = SMALL_APPLIANCE_CIRCUITS_MIN * SMALL_APPLIANCE_VA_EACH
    laundry_va = LAUNDRY_CIRCUIT_VA
    gross_va = general_lighting_va + small_appliance_va + laundry_va
    demand_va = round(_apply_standard_demand_factors(gross_va), 2)
    min_service_amps = round(demand_va / service_voltage, 2)
    min_lighting_circuits = max(1, math.ceil(general_lighting_va / (circuit_amps * 120)))

    return NecResult(
        square_feet=square_feet,
        circuit_amps=circuit_amps,
        service_voltage=service_voltage,
        general_lighting_va=round(general_lighting_va, 2),
        small_appliance_va=small_appliance_va,
        laundry_va=laundry_va,
        gross_va=round(gross_va, 2),
        demand_va=demand_va,
        min_service_amps=min_service_amps,
        min_lighting_circuits=min_lighting_circuits,
        min_small_appliance_circuits=SMALL_APPLIANCE_CIRCUITS_MIN,
        min_laundry_circuits=1,
        min_bathroom_circuits=BATHROOM_CIRCUITS_MIN,
    )


def build_material_takeoff(r: NecResult, pricebook: dict | None = None) -> list[dict]:
    """Create a square-footage planning takeoff, priced from the local pricebook.

    Layout counts and cable footage are estimating allowances, not code minimums.
    The assumed footprint is approximately square; a floor plan should replace
    these quantities before purchase or installation.
    """
    area = max(0.0, r.square_feet)
    receptacles = max(4, math.ceil(area / 50))
    light_points = max(1, math.ceil(area / 100))
    switches = light_points
    wall_boxes = receptacles + switches

    # Allow roughly 1 ft of branch cable per sq ft, plus two footprint-lengths
    # per circuit for panel home runs and routing. Round purchases up by 25 ft.
    footprint_side = math.sqrt(area)
    general_cable = area * 0.8 + r.min_lighting_circuits * footprint_side * 2
    dedicated_cable = (
        r.min_small_appliance_circuits + r.min_laundry_circuits + r.min_bathroom_circuits
    ) * footprint_side * 2
    round_25 = lambda amount: int(math.ceil(amount / 25) * 25) if amount > 0 else 0
    general_cable = round_25(general_cable)
    dedicated_cable = round_25(dedicated_cable)

    general_wire = "14/2 Romex NM-B Wire" if r.circuit_amps <= 15 else "12/2 Romex NM-B Wire"
    quantities = [
        (f"{r.circuit_amps:.0f}A Single-Pole Breaker", r.min_lighting_circuits),
        ("20A Single-Pole Breaker", r.min_small_appliance_circuits + r.min_laundry_circuits + r.min_bathroom_circuits),
        (general_wire, general_cable),
        ("12/2 Romex NM-B Wire", dedicated_cable),
        ("Duplex Outlet 15A", receptacles),
        ("Single-Pole Switch", switches),
        ("Electrical Box (single gang)", wall_boxes),
        ("Round Ceiling Box", light_points),
        ("Single-Gang Wall Plate (standard)", receptacles),
        ("Single-Gang Toggle Wall Plate", switches),
        ("Flush-Mount Ceiling Fixture", light_points),
    ]

    # Combine repeated SKUs (for example, 20A general lighting wire and
    # 20A dedicated-circuit wire) into one purchase quantity.
    combined: dict[str, int] = {}
    for name, quantity in quantities:
        combined[name] = combined.get(name, 0) + quantity
    catalog = {m["name"].casefold(): m for m in (pricebook or {}).get("materials", [])}
    rows = []
    for name, quantity in combined.items():
        if quantity <= 0:
            continue
        material = catalog.get(name.casefold())
        if material is None:
            # Keep quantity takeoff useful if a user has customized the pricebook.
            rows.append({"name": name, "quantity": quantity, "unit": "ft" if "Wire" in name else "ea", "unit_price": None, "total": None})
        else:
            rows.append({
                "name": name,
                "quantity": quantity,
                "unit": material.get("unit", "ea"),
                "unit_price": float(material.get("unit_price", 0)),
                "total": round(quantity * float(material.get("unit_price", 0)), 2),
            })
    return rows


def format_report(r: NecResult, pricebook: dict | None = None) -> str:
    total_branch_circuits = (
        r.min_lighting_circuits
        + r.min_small_appliance_circuits
        + r.min_laundry_circuits
        + r.min_bathroom_circuits
    )
    takeoff = build_material_takeoff(r, pricebook)
    material_total = sum(row["total"] or 0 for row in takeoff)
    lines = [
        f"NEC 220 quick reference for a {r.square_feet:.0f} sq ft dwelling unit",
        "-" * 60,
        f"General lighting load ({GENERAL_LIGHTING_VA_PER_SQFT} VA/sqft): {r.general_lighting_va:.0f} VA",
        f"  -> min general lighting circuits @ {r.circuit_amps:.0f}A: {r.min_lighting_circuits}",
        f"Small appliance load (220.52(A)):        {r.small_appliance_va:.0f} VA",
        f"  -> min small appliance circuits (20A):  {r.min_small_appliance_circuits}",
        f"Laundry load (220.52(B)):                 {r.laundry_va:.0f} VA",
        f"  -> min laundry circuits (20A):          {r.min_laundry_circuits}",
        f"Bathroom receptacle circuit (210.11(C)(3)): min {r.min_bathroom_circuits} dedicated 20A circuit",
        "-" * 60,
        f"Gross VA (before demand factors):  {r.gross_va:.0f} VA",
        f"Demand VA (Table 220.42 applied):  {r.demand_va:.0f} VA",
        f"Estimated min service load @ {r.service_voltage:.0f}V: {r.min_service_amps:.1f} A",
        "-" * 60,
        "Estimated material takeoff (planning quantities):",
        "  MATERIAL                         QTY UNIT    UNIT $  EXTENDED",
    ]
    for row in takeoff:
        unit_price = "TBD" if row["unit_price"] is None else f"${row['unit_price']:.2f}"
        extended = "TBD" if row["total"] is None else f"${row['total']:.2f}"
        lines.append(f"  {row['name'][:30]:<31}{row['quantity']:>5} {row['unit']:<4} {unit_price:>8} {extended:>10}")
    lines.extend([
        f"  Estimated materials subtotal: ${material_total:,.2f} (pricebook items with prices)",
        f"  Estimated branch-circuit runs: {total_branch_circuits}",
        "",
        "Planning assumptions: roughly square footprint; one duplex receptacle per 50 sq ft,",
        "one light point and switch per 100 sq ft; cable allowance = 0.8 ft/sq ft plus",
        "two footprint lengths per branch circuit. Cable purchases rounded up to 25 ft.",
        "",
        "These are area-based allowances, not a room-by-room NEC layout. Actual walls,",
        "kitchen/bath requirements, fixture choices, routing, and panel compatibility can",
        "change quantities. Confirm against the floor plan and local code before ordering.",
        "-" * 60,
        "NOTE: Base minimums only (lighting/receptacle/small appliance/laundry).",
        "Does NOT include ranges, dryers, water heaters, HVAC, EVSE, or other",
        "fixed appliances. Verify against a full NEC 220 calculation, local",
        "amendments, and your AHJ before finalizing service/panel sizing.",
    ])
    return "\n".join(lines)
