"""Job snapshots, decimal cost calculations, and transactional crew scheduling."""
from __future__ import annotations

from contextlib import closing, contextmanager
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_CEILING
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

CENT = Decimal("0.01")


class JobError(ValueError):
    status_code = 400


class Conflict(JobError):
    status_code = 409


class NotFound(JobError):
    status_code = 404


def number(value, name: str, maximum: str = "10000000") -> Decimal:
    if isinstance(value, bool) or len(str(value)) > 40:
        raise JobError(f"{name} must be a non-negative number.")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise JobError(f"{name} must be a non-negative number.") from exc
    if not result.is_finite() or result < 0 or result > Decimal(maximum):
        raise JobError(f"{name} must be between 0 and {maximum}.")
    exponent = result.as_tuple().exponent
    if not isinstance(exponent, int) or not -6 <= exponent <= 7:
        raise JobError(f"{name} must use at most six decimal places and a supported magnitude.")
    return result


def money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def text(value, name: str, limit: int = 2000, required: bool = False) -> str:
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise JobError(f"{name} must be {'non-empty ' if required else ''}text (up to {limit} characters).")
    return value.strip()


def flag(value, name: str) -> bool:
    if not isinstance(value, bool):
        raise JobError(f"{name} must be true or false.")
    return value


def iso_date(value, name: str, optional: bool = True) -> str:
    value = text(value, name, 10, not optional)
    if not value and optional:
        return ""
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise JobError(f"{name} must be a date (YYYY-MM-DD).") from exc


def timestamp(value) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError) as exc:
        raise JobError("Start must be an ISO timestamp including a timezone.") from exc


def normalize_job(data: dict) -> dict:
    if not isinstance(data, dict):
        raise JobError("Job must be an object.")
    job = {
        key: text(data.get(key, ""), key, limit, required)
        for key, limit, required in (
            ("title", 160, True), ("customer", 160, False), ("address", 500, False),
            ("scope", 6000, False), ("exclusions", 4000, False), ("notes", 4000, False),
        )
    }
    for key in ("labor_rate", "permits", "equipment", "other_costs"):
        job[key] = str(number(data.get(key, "0"), key))
    for key in ("overhead_percent", "contingency_percent", "pricing_percent", "tax_percent", "consumables_percent"):
        maximum = "99.99" if key == "pricing_percent" and data.get("pricing_mode") == "margin" else "100"
        job[key] = str(number(data.get(key, "0"), key, maximum))
    job["pricing_mode"] = data.get("pricing_mode", "markup")
    job["tax_mode"] = data.get("tax_mode", "none")
    if job["pricing_mode"] not in ("markup", "margin") or job["tax_mode"] not in ("none", "materials", "all"):
        raise JobError("Choose a supported pricing mode and tax treatment.")
    for key in ("tax_confirmed", "labor_confirmed", "scope_confirmed"):
        job[key] = flag(data.get(key, False), key)
    job["valid_until"] = iso_date(data.get("valid_until", ""), "Quote expiration")
    items = data.get("items", [])
    if not isinstance(items, list) or len(items) > 250:
        raise JobError("Items must be a list of up to 250 rows.")
    job["items"] = []
    for item in items:
        if not isinstance(item, dict):
            raise JobError("Each item must be an object.")
        row = {
            key: text(item.get(key, ""), key, limit, required)
            for key, limit, required in (
                ("description", 240, True), ("unit", 20, True),
                ("supplier", 240, False), ("specification", 500, False),
            )
        }
        for key, maximum in (("quantity", "1000000"), ("unit_cost", "10000000"),
                             ("hours_per_unit", "10000"), ("waste_percent", "100")):
            row[key] = str(number(item.get(key, "0"), key, maximum))
        if Decimal(row["quantity"]) == 0:
            raise JobError("Item quantities must be greater than zero.")
        row["customer_supplied"] = flag(item.get("customer_supplied", False), "customer_supplied")
        if row["customer_supplied"] and Decimal(row["unit_cost"]) != 0:
            raise JobError("Customer-supplied materials must have zero material cost.")
        row["verified_on"] = iso_date(item.get("verified_on", ""), "Price verification date")
        if row["verified_on"] and date.fromisoformat(row["verified_on"]) > date.today():
            raise JobError("Price verification dates cannot be in the future.")
        job["items"].append(row)
    return job


def calculate(job: dict, today: date | None = None) -> dict:
    """Round each extended material cost, then aggregate with decimal arithmetic."""
    today = today or date.today()
    material = Decimal(0)
    hours = Decimal(0)
    warnings = []
    rows = []
    for index, row in enumerate(job["items"], 1):
        quantity = Decimal(row["quantity"])
        cost = Decimal(money(quantity * Decimal(row["unit_cost"]) *
                             (1 + Decimal(row["waste_percent"]) / 100)))
        line_hours = quantity * Decimal(row["hours_per_unit"])
        material += cost
        hours += line_hours
        rows.append({"material": money(cost), "labor_hours": str(line_hours)})
        if not row["customer_supplied"]:
            if Decimal(row["unit_cost"]) == 0:
                warnings.append(f"Row {index}: material price is missing.")
            if not row["supplier"] or not row["specification"] or not row["verified_on"]:
                warnings.append(f"Row {index}: confirm supplier, exact specification, and price date.")
            elif (today - date.fromisoformat(row["verified_on"])).days > 30:
                warnings.append(f"Row {index}: material price is over 30 days old.")
    consumables = Decimal(money(material * Decimal(job["consumables_percent"]) / 100))
    materials = material + consumables
    labor = Decimal(money(hours * Decimal(job["labor_rate"])))
    direct = materials + labor + sum(Decimal(job[key]) for key in ("permits", "equipment", "other_costs"))
    direct = Decimal(money(direct))
    overhead = Decimal(money(direct * Decimal(job["overhead_percent"]) / 100))
    contingency = Decimal(money(direct * Decimal(job["contingency_percent"]) / 100))
    cost_basis = direct + overhead + contingency
    percent = Decimal(job["pricing_percent"]) / 100
    selling = cost_basis / (1 - percent) if job["pricing_mode"] == "margin" else cost_basis * (1 + percent)
    selling = Decimal(money(selling))
    if selling > Decimal("9999999999.99"):
        raise JobError("Estimate exceeds the supported selling-price limit of $9,999,999,999.99.")
    profit = selling - cost_basis
    taxable = selling if job["tax_mode"] == "all" else Decimal(0)
    if job["tax_mode"] == "materials" and direct:
        taxable = Decimal(money(selling * materials / direct))
    tax = Decimal(money(taxable * Decimal(job["tax_percent"]) / 100))
    if not job["items"]:
        warnings.append("Add at least one estimate item.")
    if hours <= 0 or Decimal(job["labor_rate"]) <= 0 or not job["labor_confirmed"]:
        warnings.append("Confirm positive labor hours and your fully burdened hourly cost.")
    if not job["tax_confirmed"]:
        warnings.append("Confirm tax treatment with your accountant; no jurisdiction is inferred.")
    if not job["scope_confirmed"] or not job["scope"] or not job["customer"] or not job["address"]:
        warnings.append("Confirm the customer, site address, and complete scope.")
    if not job["valid_until"] or date.fromisoformat(job["valid_until"]) < today:
        warnings.append("Set a quote expiration date that has not passed.")
    return {
        "rows": rows, "materials": money(materials), "consumables": money(consumables),
        "labor_hours": str(hours), "labor": money(labor), "direct_cost": money(direct),
        "overhead": money(overhead), "contingency": money(contingency),
        "cost_basis": money(cost_basis), "profit_allowance": money(profit),
        "subtotal": money(selling), "taxable": money(taxable), "tax": money(tax),
        "total": money(selling + tax),
        "margin_percent": money(profit / selling * 100) if selling else "0.00",
        "markup_percent": money(profit / cost_basis * 100) if cost_basis else "0.00",
        "warnings": warnings,
    }


def new_job(title: str = "New estimate") -> dict:
    return normalize_job({"title": title, "valid_until": (date.today() + timedelta(days=30)).isoformat()})


def built_in_templates(pricebook: dict) -> list[dict]:
    """Starter allowances, not engineered designs or verified labor standards."""
    catalog = {row["name"]: row for row in pricebook["materials"]}
    definitions = (
        ("outlet", "Outlet replacement", "Replace one existing outlet; accessible wiring in sound condition.",
         "New circuits, concealed damage, wall repairs, and code corrections outside this scope.",
         (("Duplex Outlet 15A", 1, ".4"), ("Single-Gang Wall Plate (standard)", 1, ".1"))),
        ("lighting", "Four recessed lights", "Install four recessed lights with accessible wiring routes.",
         "Drywall repairs, painting, new home runs, and concealed obstructions.",
         (("4-in LED Recessed Wafer Light", 4, ".75"), ("14/2 Romex NM-B Wire", 80, ".015"),
          ("Single-Pole Switch", 1, ".4"))),
        ("ev", "EV circuit planning allowance", "Draft allowance for a dedicated EV charging circuit; site survey required.",
         "EVSE equipment, trenching, service upgrades, permits, and utility work unless added. "
         "Confirm load calculation, conductor sizing, protection, and manufacturer instructions.",
         (("50A Two-Pole Breaker (range/EVSE)", 1, "1"), ("EMT Conduit 3/4 in", 30, ".08"))),
        ("panel", "Panel replacement planning allowance", "Draft panel replacement allowance; site and service survey required.",
         "Utility fees, service conductors, all branch breakers, permits, repairs, and service upgrades unless added. "
         "Confirm AHJ, utility requirements, compatibility, grounding, and bonding.",
         (("200A Load Center Panel", 1, "12"), ("Ground Rod 8ft Copper-Clad", 2, ".75"),
          ("Ground Rod Clamp", 2, ".1"))),
    )
    result = []
    for key, title, scope, exclusions, items in definitions:
        job = new_job(title)
        job.update(scope=scope, exclusions=exclusions,
                   notes="Starter quantities and labor hours are unverified allowances. Complete a site survey. "
                         "Add all missing materials, permits, travel, and labor before quoting.")
        for name, quantity, hours in items:
            material = catalog[name]
            job["items"].append({
                "description": name, "quantity": str(quantity), "unit": material["unit"],
                "unit_cost": str(material["unit_price"]), "hours_per_unit": hours,
                "waste_percent": "0", "supplier": "", "specification": "",
                "verified_on": "", "customer_supplied": False,
            })
        if key in ("ev", "panel"):
            job["items"].append({
                "description": ("Circuit conductors and fittings - site-specific allowance" if key == "ev"
                                else "Compatible branch breakers and connectors - site-specific allowance"),
                "quantity": "1", "unit": "lot", "unit_cost": "0", "hours_per_unit": "0",
                "waste_percent": "0", "supplier": "", "specification": "",
                "verified_on": "", "customer_supplied": False,
            })
        result.append({"id": key, "name": title, "job": job, "built_in": True})
    return result


class JobStore:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS job_records (
                    id TEXT PRIMARY KEY, version INTEGER NOT NULL, data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS job_templates (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, data TEXT NOT NULL
                );
            """)

    @contextmanager
    def connection(self, write: bool = False):
        with closing(sqlite3.connect(self.path, timeout=15)) as db:
            with db:
                db.row_factory = sqlite3.Row
                if write:
                    db.execute("BEGIN IMMEDIATE")
                yield db

    def _get(self, db, job_id: str) -> dict:
        row = db.execute("SELECT data FROM job_records WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise NotFound("Job not found.")
        return json.loads(row["data"])

    def get(self, job_id: str) -> dict:
        with self.connection() as db:
            return self._get(db, job_id)

    def list(self) -> list[dict]:
        with self.connection() as db:
            return [json.loads(row["data"]) for row in db.execute("SELECT data FROM job_records ORDER BY rowid DESC")]

    def _save(self, db, job: dict) -> dict:
        job["version"] += 1
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        db.execute("INSERT INTO job_records VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE "
                   "SET version=excluded.version, data=excluded.data",
                   (job["id"], job["version"], json.dumps(job)))
        return job

    def create(self, data: dict, source_id: str = "") -> dict:
        job = normalize_job(data)
        calculate(job)
        job.update(id=uuid4().hex, version=0, status="draft", schedule=None, actual=None,
                   quote_totals=None, source_id=source_id)
        with self.connection(write=True) as db:
            return self._save(db, job)

    def _check_version(self, job: dict, version):
        if type(version) is not int or version != job["version"]:
            raise Conflict("This job changed in another window. Reload it before saving.")

    def update(self, job_id: str, data: dict, version) -> dict:
        clean = normalize_job(data)
        calculate(clean)
        with self.connection(write=True) as db:
            job = self._get(db, job_id)
            self._check_version(job, version)
            if job["status"] != "draft":
                raise Conflict("Quoted scope and prices are locked. Create a revision instead.")
            job.update(clean)
            return self._save(db, job)

    def transition(self, job_id: str, action: str, version) -> dict:
        with self.connection(write=True) as db:
            job = self._get(db, job_id)
            self._check_version(job, version)
            if action == "quote" and job["status"] == "draft":
                totals = calculate(job)
                if totals["warnings"]:
                    raise JobError("Resolve the quote checks before quoting: " + " ".join(totals["warnings"]))
                job.update(status="quoted", quote_totals=totals,
                           quoted_at=datetime.now(timezone.utc).isoformat())
            elif action == "accept" and job["status"] == "quoted":
                if date.fromisoformat(job["valid_until"]) < date.today():
                    raise Conflict("This quote has expired. Create a revision.")
                job.update(status="accepted", accepted_at=datetime.now(timezone.utc).isoformat())
            elif action == "complete" and job["status"] == "scheduled":
                if job["actual"] is None:
                    raise JobError("Record actual hours and costs before completing the job.")
                job["status"] = "completed"
            elif action == "unschedule" and job["status"] == "scheduled":
                job.update(status="accepted", schedule=None)
            else:
                raise Conflict("That action is not available in the current job status.")
            return self._save(db, job)

    def revise(self, job_id: str) -> dict:
        source = self.get(job_id)
        data = deepcopy(source)
        data["title"] = source["title"][:145] + " (revision)"
        data["valid_until"] = (date.today() + timedelta(days=30)).isoformat()
        for key in ("scope_confirmed", "tax_confirmed", "labor_confirmed"):
            data[key] = False
        return self.create(data, source_id=source["id"])

    def schedule(self, job_id: str, data: dict) -> dict:
        start = timestamp(data.get("start"))
        raw_crew = data.get("crew")
        if not isinstance(raw_crew, list) or not 1 <= len(raw_crew) <= 30:
            raise JobError("Choose between 1 and 30 crew members.")
        crew = [text(member, "Crew member", 100, True) for member in raw_crew]
        if len({member.casefold() for member in crew}) != len(crew):
            raise JobError("Crew members must be unique.")
        travel = number(data.get("travel_hours", 0), "Travel elapsed hours", "1000")
        buffer = number(data.get("buffer_hours", 0), "On-site buffer hours", "1000")
        ready_on = iso_date(data.get("ready_on", ""), "Materials / permits ready date", optional=False)
        # Compare calendar dates in the timezone supplied by the dispatcher.
        local_start = datetime.fromisoformat(data["start"])
        if local_start.date() < date.fromisoformat(ready_on):
            raise JobError("Work cannot start before materials and permits are ready.")
        override = text(data.get("override_reason", ""), "Conflict override reason", 1000)
        with self.connection(write=True) as db:
            job = self._get(db, job_id)
            self._check_version(job, data.get("version"))
            if job["status"] not in ("accepted", "scheduled"):
                raise Conflict("Accept the quote before scheduling.")
            hours = Decimal(job["quote_totals"]["labor_hours"]) / len(crew) + travel + buffer
            minutes = int((hours * 60).to_integral_value(rounding=ROUND_CEILING))
            if minutes <= 0:
                raise JobError("Scheduled duration must be positive.")
            if minutes > 31 * 24 * 60:
                raise JobError("A reservation cannot exceed 31 days. Split this work into smaller jobs.")
            try:
                end = start + timedelta(minutes=minutes)
            except OverflowError as exc:
                raise JobError("Schedule end is outside the supported date range.") from exc
            conflicts = []
            for row in db.execute("SELECT data FROM job_records WHERE id != ?", (job_id,)):
                other = json.loads(row["data"])
                slot = other["schedule"]
                if other["status"] != "scheduled" or not slot:
                    continue
                shared = {member.casefold() for member in crew} & {member.casefold() for member in slot["crew"]}
                if shared and start < timestamp(slot["end"]) and end > timestamp(slot["start"]):
                    conflicts.append(other["title"])
            if conflicts and not override:
                raise Conflict("Crew conflict with: " + ", ".join(conflicts) + ". Adjust the start or enter an override reason.")
            job["schedule"] = {
                "start": start.isoformat(), "end": end.isoformat(), "crew": crew,
                "travel_hours": str(travel), "buffer_hours": str(buffer), "ready_on": ready_on,
                "override_reason": override, "conflicts": conflicts, "duration_minutes": minutes,
            }
            job["status"] = "scheduled"
            return self._save(db, job)

    def actuals(self, job_id: str, data: dict) -> dict:
        actual = {key: str(number(data.get(key), key)) for key in (
            "labor_hours", "labor_cost", "materials", "permits", "equipment", "other_costs")}
        actual["notes"] = text(data.get("notes", ""), "Actual cost notes", 4000)
        with self.connection(write=True) as db:
            job = self._get(db, job_id)
            self._check_version(job, data.get("version"))
            if job["status"] not in ("accepted", "scheduled", "completed"):
                raise Conflict("Accept the quote before recording actual costs.")
            job["actual"] = actual
            return self._save(db, job)

    def save_template(self, job_id: str, name: str) -> dict:
        job = normalize_job(self.get(job_id))
        for key in ("customer", "address", "notes", "valid_until"):
            job[key] = ""
        for key in ("tax_confirmed", "labor_confirmed", "scope_confirmed"):
            job[key] = False
        template = {"id": uuid4().hex, "name": text(name, "Template name", 160, True),
                    "job": job, "built_in": False}
        with self.connection(write=True) as db:
            db.execute("INSERT INTO job_templates VALUES (?, ?, ?)",
                       (template["id"], template["name"], json.dumps(template)))
        return template

    def templates(self) -> list[dict]:
        with self.connection() as db:
            return [json.loads(row["data"]) for row in db.execute("SELECT data FROM job_templates ORDER BY name")]


def job_view(job: dict) -> dict:
    result = deepcopy(job)
    result["totals"] = job["quote_totals"] or calculate(job)
    result["comparison"] = None
    if job["actual"] is not None:
        actual = job["actual"]
        cost = sum(Decimal(actual[key]) for key in ("labor_cost", "materials", "permits", "equipment", "other_costs"))
        result["comparison"] = {
            "actual_cost": money(cost),
            "direct_cost_variance": money(cost - Decimal(result["totals"]["direct_cost"])),
            "labor_hours_variance": str(Decimal(actual["labor_hours"]) - Decimal(result["totals"]["labor_hours"])),
            "remaining_before_overhead": money(Decimal(result["totals"]["subtotal"]) - cost),
        }
    return result
