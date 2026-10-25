"""Data models for the electrical estimator (stdlib only, no dependencies)."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class MaterialItem:
    name: str
    unit: str
    unit_price: float
    labor_unit_price: float = 0.0  # labor cost baked into each unit, e.g. $/ft installed
    category: str = "Other"


@dataclass
class LineItem:
    description: str
    quantity: float
    unit: str
    unit_price: float
    labor_hours: float = 0.0
    labor_unit_price: float = 0.0

    @property
    def material_total(self) -> float:
        return round(self.quantity * self.unit_price, 2)

    def labor_total(self, labor_rate_per_hour: float) -> float:
        return round(self.labor_hours * labor_rate_per_hour + self.quantity * self.labor_unit_price, 2)

    def line_total(self, labor_rate_per_hour: float) -> float:
        return round(self.material_total + self.labor_total(labor_rate_per_hour), 2)


@dataclass
class Estimate:
    title: str
    labor_rate_per_hour: float
    tax_rate_percent: float
    markup_percent: float = 0.0
    consumables_percent: float = 0.0
    state: str = "Maryland"
    local_jurisdiction: str = ""
    code_edition: str = "2020 NEC (Maryland baseline; confirm local amendments)"
    line_items: list[LineItem] = field(default_factory=list)
    created: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def materials_subtotal(self) -> float:
        return round(sum(li.material_total for li in self.line_items), 2)

    @property
    def labor_subtotal(self) -> float:
        return round(sum(li.labor_total(self.labor_rate_per_hour) for li in self.line_items), 2)

    @property
    def markup_amount(self) -> float:
        # Markup is applied to materials cost only, a common contractor convention.
        return round(self.materials_subtotal * (self.markup_percent / 100), 2)

    @property
    def consumables_amount(self) -> float:
        # Covers small unlisted consumables (wire nuts, staples, tape, etc.) as a
        # percentage of materials cost, instead of itemizing every box of nuts.
        return round(self.materials_subtotal * (self.consumables_percent / 100), 2)

    @property
    def subtotal(self) -> float:
        return round(self.materials_subtotal + self.markup_amount + self.consumables_amount + self.labor_subtotal, 2)

    @property
    def tax(self) -> float:
        return round(self.subtotal * (self.tax_rate_percent / 100), 2)

    @property
    def total(self) -> float:
        return round(self.subtotal + self.tax, 2)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @staticmethod
    def from_dict(d: dict) -> "Estimate":
        items = [LineItem(**li) for li in d.get("line_items", [])]
        est = Estimate(
            title=d["title"],
            labor_rate_per_hour=d["labor_rate_per_hour"],
            tax_rate_percent=d["tax_rate_percent"],
            markup_percent=d.get("markup_percent", 0.0),
            consumables_percent=d.get("consumables_percent", 0.0),
            state=d.get("state", "Maryland"),
            local_jurisdiction=d.get("local_jurisdiction", ""),
            code_edition=d.get("code_edition", "2020 NEC (Maryland baseline; confirm local amendments)"),
            line_items=items,
            created=d.get("created", datetime.now().isoformat(timespec="seconds")),
        )
        return est

