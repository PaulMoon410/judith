"""File I/O helpers: pricebook and saved estimates (JSON, stdlib only)."""
from __future__ import annotations

import csv
import json
import os
import time
from typing import Any

from .models import Estimate, MaterialItem

AI_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60


def get_ai_cache(pricebook: dict[str, Any]) -> dict[str, Any]:
    return pricebook.setdefault("ai_cache", {})


def get_cached_ai_value(pricebook: dict[str, Any], key: str) -> Any:
    entry = get_ai_cache(pricebook).get(key)
    if not isinstance(entry, dict):
        return None
    if time.time() - float(entry.get("ts", 0)) > AI_CACHE_TTL_SECONDS:
        return None
    return entry.get("value")


def set_cached_ai_value(pricebook: dict[str, Any], key: str, value: Any) -> None:
    get_ai_cache(pricebook)[key] = {"ts": time.time(), "value": value}
def _ftp_config():
    host = os.environ.get("FTP_HOST", "").strip()
    if not host:
        return None
    return (
        host,
        os.environ.get("FTP_USER", "").strip(),
        os.environ.get("FTP_PASS", "").strip(),
        os.environ.get("FTP_PRICEBOOK_PATH", "/ai/brain/pricebook.json").strip(),
    )


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ESTIMATES_DIR = os.path.join(BASE_DIR, "estimates")
PRICEBOOK_PATH = os.path.join(DATA_DIR, "pricebook.json")


def _ftp_load(path, host, user, password):
    try:
        buf = io.BytesIO()
        with ftplib.FTP(host, timeout=20) as ftp:
            ftp.login(user, password)
            ftp.retrbinary("RETR " + path, buf.write)
        return json.loads(buf.getvalue().decode("utf-8"))
    except Exception:
        return None


def _ftp_save(path, host, user, password, data):
    try:
        buf = io.BytesIO(json.dumps(data, indent=2).encode("utf-8"))
        with ftplib.FTP(host, timeout=20) as ftp:
            ftp.login(user, password)
            ftp.storbinary("STOR " + path, buf)
        return True
    except Exception:
        return False


def load_pricebook() -> dict[str, Any]:
    cfg = _ftp_config()
    if cfg:
        host, user, password, path = cfg
        data = _ftp_load(path, host, user, password)
        if data is not None:
            return data
    with open(PRICEBOOK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pricebook(pricebook: dict[str, Any]) -> None:
    cfg = _ftp_config()
    if cfg:
        host, user, password, path = cfg
        if _ftp_save(path, host, user, password, pricebook):
            return
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PRICEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(pricebook, f, indent=2)


def get_materials(pricebook: dict[str, Any]) -> list[MaterialItem]:
    return [MaterialItem(**m) for m in pricebook.get("materials", [])]


def get_categories(pricebook: dict[str, Any]) -> list[str]:
    seen: list[str] = []
    for m in get_materials(pricebook):
        if m.category not in seen:
            seen.append(m.category)
    return seen


def get_materials_by_category(pricebook: dict[str, Any], category: str) -> list[MaterialItem]:
    return [m for m in get_materials(pricebook) if m.category == category]


def get_labor_rate(pricebook: dict[str, Any]) -> float:
    """Return the pricebook's active labor rate, falling back to the multi-source
    recommendation if none is stored."""
    from . import labor_rates

    if "labor_rate_per_hour" in pricebook:
        try:
            return float(pricebook["labor_rate_per_hour"])
        except (TypeError, ValueError):
            pass
    state = pricebook.get("state", "Maryland")
    return labor_rates.compare_rates(state).recommended


def get_labor_rate_sources(pricebook: dict[str, Any]) -> list[dict]:
    """Return user-added/refreshed labor rate sources stored in the pricebook."""
    return list(pricebook.get("labor_rate_sources", []))


def set_labor_rate(pricebook: dict[str, Any], rate: float) -> None:
    """Persist the active labor rate into the pricebook."""
    pricebook["labor_rate_per_hour"] = round(float(rate), 2)


def set_labor_rate_sources(pricebook: dict[str, Any], sources: list[dict]) -> None:
    """Persist additional labor rate sources into the pricebook."""
    pricebook["labor_rate_sources"] = sources


def _safe_filename(title: str) -> str:
    keep = "".join(c if c.isalnum() or c in " _-" else "_" for c in title).strip()
    return keep.replace(" ", "_") or "estimate"


def save_estimate(estimate: Estimate) -> str:
    os.makedirs(ESTIMATES_DIR, exist_ok=True)
    filename = _safe_filename(estimate.title) + ".json"
    path = os.path.join(ESTIMATES_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(estimate.to_dict(), f, indent=2)
    return path


def list_saved_estimates() -> list[str]:
    if not os.path.isdir(ESTIMATES_DIR):
        return []
    return sorted(f for f in os.listdir(ESTIMATES_DIR) if f.endswith(".json"))


def load_estimate(filename: str) -> Estimate:
    path = os.path.join(ESTIMATES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return Estimate.from_dict(json.load(f))


def export_text_report(estimate: Estimate) -> str:
    os.makedirs(ESTIMATES_DIR, exist_ok=True)
    filename = _safe_filename(estimate.title) + ".txt"
    path = os.path.join(ESTIMATES_DIR, filename)
    lines = []
    lines.append(f"ELECTRICAL WORK ESTIMATE - {estimate.title}")
    lines.append(f"Date: {estimate.created}")
    locality = f", {estimate.local_jurisdiction}" if estimate.local_jurisdiction else ""
    lines.append(f"Project jurisdiction: {estimate.state}{locality}")
    lines.append(f"Electrical code reference: {estimate.code_edition}")
    lines.append("Quick calculation rules are not yet adjusted by state or code edition.")
    lines.append("Confirm local adoption and amendments with the authority having jurisdiction.")
    lines.append("-" * 60)
    lines.append(f"{'Description':<28}{'Qty':>6}{'Unit':>6}{'$/Unit':>10}{'Line $':>10}")
    lines.append("-" * 60)
    for li in estimate.line_items:
        lines.append(
            f"{li.description[:28]:<28}{li.quantity:>6.2f}{li.unit:>6}"
            f"{li.unit_price:>10.2f}{li.line_total(estimate.labor_rate_per_hour):>10.2f}"
        )
        if li.labor_hours:
            lines.append(f"    labor: {li.labor_hours:.2f} hr @ ${estimate.labor_rate_per_hour:.2f}/hr")
    lines.append("-" * 60)
    lines.append(f"{'Materials subtotal':<40}{estimate.materials_subtotal:>20.2f}")
    if estimate.markup_percent:
        lines.append(f"{'Markup (' + str(estimate.markup_percent) + '%)':<40}{estimate.markup_amount:>20.2f}")
    lines.append(f"{'Labor subtotal':<40}{estimate.labor_subtotal:>20.2f}")
    lines.append(f"{'Subtotal':<40}{estimate.subtotal:>20.2f}")
    lines.append(f"{'Tax (' + str(estimate.tax_rate_percent) + '%)':<40}{estimate.tax:>20.2f}")
    lines.append(f"{'TOTAL':<40}{estimate.total:>20.2f}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def export_csv_report(estimate: Estimate) -> str:
    os.makedirs(ESTIMATES_DIR, exist_ok=True)
    filename = _safe_filename(estimate.title) + ".csv"
    path = os.path.join(ESTIMATES_DIR, filename)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Project state", estimate.state])
        writer.writerow(["Local jurisdiction", estimate.local_jurisdiction])
        writer.writerow(["Electrical code basis", estimate.code_edition])
        writer.writerow(["Description", "Quantity", "Unit", "Unit Price", "Labor Hours", "Labor Total", "Line Total"])
        for li in estimate.line_items:
            writer.writerow([
                li.description,
                li.quantity,
                li.unit,
                li.unit_price,
                li.labor_hours,
                li.labor_total(estimate.labor_rate_per_hour),
                li.line_total(estimate.labor_rate_per_hour),
            ])
        writer.writerow([])
        writer.writerow(["Materials subtotal", estimate.materials_subtotal])
        if estimate.markup_percent:
            writer.writerow([f"Markup ({estimate.markup_percent}%)", estimate.markup_amount])
        writer.writerow(["Labor subtotal", estimate.labor_subtotal])
        writer.writerow(["Subtotal", estimate.subtotal])
        writer.writerow([f"Tax ({estimate.tax_rate_percent}%)", estimate.tax])
        writer.writerow(["TOTAL", estimate.total])
    return path
