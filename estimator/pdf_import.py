"""Create a draft estimate from quantity/material rows in a text-based PDF.

This intentionally does not infer quantities from drawing geometry or run OCR.
Imported line items are estimates for review, not a verified material takeoff.
"""
from __future__ import annotations

import os
import re

from pypdf import PdfReader

from .models import Estimate, LineItem, MaterialItem
from .storage import get_materials

_NUMBER = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_UNITS = {
    "ea": "ea", "each": "ea", "pc": "ea", "pcs": "ea", "pieces": "ea",
    "ft": "ft", "feet": "ft", "lf": "ft", "in": "in", "inch": "in",
    "inches": "in", "m": "m", "meters": "m", "box": "box", "boxes": "box",
    "roll": "roll", "rolls": "roll", "lot": "lot", "hr": "hr", "hrs": "hr",
    "hour": "hr", "hours": "hr",
}
_LEADING_ROW = re.compile(
    rf"^\s*({_NUMBER})(?:\s*(ea|each|pcs?|pieces|ft|feet|lf|inches|inch|in|meters|m|boxes|box|rolls|roll|hours|hour|hrs?|lot))?\s+(?:[-:x×]\s*)?(.+?)\s*$",
    re.IGNORECASE,
)
_TRAILING_ROW = re.compile(
    rf"^\s*(.+?)\s+(?:x|×)\s*({_NUMBER})\s*(ea|each|pcs?|ft|feet|lf|in|box|roll|hr|hrs|lot)?\s*$",
    re.IGNORECASE,
)
_TRAILING_COUNT = re.compile(
    rf"^\s*(.+?)\s+({_NUMBER})\s*(ea|each|pcs?|ft|feet|lf|in|box|roll|hr|hrs|lot)\s*$",
    re.IGNORECASE,
)
_IGNORED_DESCRIPTION = re.compile(r"\b(?:qty|quantity|subtotal|total|page|date|description|unit price)\b", re.I)


def extract_pdf_text(path: str) -> str:
    """Extract selectable text from a PDF, raising a useful error if unavailable."""
    if not path.lower().endswith(".pdf"):
        raise ValueError("Please choose a PDF file.")
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ValueError("This PDF is password-protected and cannot be imported.")
        pages = [page.extract_text() or "" for page in reader.pages]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not read this PDF: {exc}") from exc
    text = "\n".join(pages).strip()
    if not text:
        raise ValueError(
            "No selectable text was found. This may be a scanned/drawing-only PDF; "
            "OCR and quantity takeoff from drawing geometry are not supported yet."
        )
    return text


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _match_material(description: str, materials: list[MaterialItem]) -> MaterialItem | None:
    normalized = _normalize(description)
    exact = [material for material in materials if _normalize(material.name) == normalized]
    if exact:
        return exact[0]
    matches = [
        material for material in materials
        if _normalize(material.name) in normalized or normalized in _normalize(material.name)
    ]
    return max(matches, key=lambda material: len(_normalize(material.name)), default=None)


def parse_quantity_rows(text: str, pricebook: dict) -> tuple[list[LineItem], int]:
    """Parse explicit quantity rows; return line items and catalog-match count."""
    materials = get_materials(pricebook)
    rows: dict[str, LineItem] = {}
    matched_keys: set[str] = set()

    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" \t|•·")
        if not line or _IGNORED_DESCRIPTION.search(line):
            continue

        match = _LEADING_ROW.match(line)
        if match:
            quantity, unit, description = match.groups()
        else:
            match = _TRAILING_ROW.match(line) or _TRAILING_COUNT.match(line)
            if not match:
                continue
            description, quantity, unit = match.groups()

        description = description.strip(" -:|\t")
        if len(description) < 2 or not re.search(r"[a-zA-Z]", description):
            continue
        try:
            quantity_value = float(quantity.replace(",", ""))
        except ValueError:
            continue
        if quantity_value <= 0 or quantity_value > 1_000_000:
            continue

        material = _match_material(description, materials)
        if material:
            name = material.name
            item_unit = material.unit
            unit_price = material.unit_price
            labor_unit_price = material.labor_unit_price
            matched_keys.add(_normalize(name))
        else:
            name = description
            item_unit = _UNITS.get((unit or "").casefold(), "ea")
            unit_price = 0.0
            labor_unit_price = 0.0

        key = _normalize(name)
        if key in rows:
            rows[key].quantity += quantity_value
        else:
            rows[key] = LineItem(
                description=name,
                quantity=quantity_value,
                unit=item_unit,
                unit_price=unit_price,
                labor_unit_price=labor_unit_price,
            )

    return list(rows.values()), len(matched_keys)


def create_estimate_from_pdf(path: str, pricebook: dict) -> tuple[Estimate, int]:
    """Build a draft from explicit PDF quantity rows and local defaults."""
    text = extract_pdf_text(path)
    line_items, matched_count = parse_quantity_rows(text, pricebook)
    if not line_items:
        raise ValueError(
            "The PDF text was readable, but no clear material/quantity rows were found. "
            "Use a PDF with a bill of materials or item schedule, or create the estimate manually."
        )
    estimate = Estimate(
        title=os.path.splitext(os.path.basename(path))[0],
        labor_rate_per_hour=float(pricebook.get("labor_rate_per_hour", 65.0)),
        tax_rate_percent=float(pricebook.get("tax_rate_percent", 0.0)),
        markup_percent=float(pricebook.get("markup_percent", 0.0)),
        consumables_percent=float(pricebook.get("consumables_percent", 0.0)),
        line_items=line_items,
    )
    return estimate, matched_count