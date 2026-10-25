"""Terminal menu UI for the electrical work estimator (stdlib only)."""
from __future__ import annotations

from datetime import datetime

from .models import Estimate, LineItem
from . import labor_rates, material_prices, nec, storage, ui


def _round_money(value: float) -> float:
    return round(float(value), 2)


def prompt_float(prompt: str, default: float | None = None) -> float:
    while True:
        raw = input(prompt).strip()
        if not raw and default is not None:
            return default
        try:
            return float(raw)
        except ValueError:
            print("  Please enter a number.")


def prompt_nonempty(prompt: str, default: str | None = None) -> str:
    while True:
        raw = input(prompt).strip()
        if raw:
            return raw
        if default is not None:
            return default
        print("  This field is required.")


def choose_material(pricebook: dict) -> tuple[str, str, float, float] | None:
    materials = storage.get_materials(pricebook)
    if not materials:
        print("  No materials in pricebook.")
        return None
    last_category = None
    for i, m in enumerate(materials, start=1):
        if m.category != last_category:
            print(ui.bold(ui.magenta(f"  --- {m.category} ---")))
            last_category = m.category
        installed = m.unit_price + m.labor_unit_price
        labor_note = ui.dim(f" (incl. ${m.labor_unit_price:.2f} labor)") if m.labor_unit_price else ""
        print(f"  {ui.bold_cyan(f'{i:>2}')}. {m.name:<30} {installed:>8.2f} / {m.unit}{labor_note}")
    print(f"  {ui.bold_cyan(f'{len(materials) + 1:>2}')}. Custom (not in pricebook)")
    choice = prompt_nonempty("Select material #: ")
    try:
        idx = int(choice)
    except ValueError:
        print("  Invalid selection.")
        return None
    if 1 <= idx <= len(materials):
        m = materials[idx - 1]
        return m.name, m.unit, m.unit_price, m.labor_unit_price
    if idx == len(materials) + 1:
        name = prompt_nonempty("  Custom item name: ")
        unit = prompt_nonempty("  Unit (ea/ft/box/...): ", default="ea")
        price = prompt_float("  Material unit price: $", default=0.0)
        labor_unit_price = prompt_float("  Labor $/unit already included (0 if using hours instead): $", default=0.0)
        return name, unit, price, labor_unit_price
    print("  Invalid selection.")
    return None


def add_line_item(estimate: Estimate, pricebook: dict) -> None:
    picked = choose_material(pricebook)
    if picked is None:
        return
    name, unit, price, labor_unit_price = picked
    qty = prompt_float(f"Quantity ({unit}): ", default=1.0)
    labor_hours = 0.0
    if not labor_unit_price:
        labor_hours = prompt_float("Labor hours for this item (0 if none): ", default=0.0)
    estimate.line_items.append(
        LineItem(
            description=name,
            quantity=qty,
            unit=unit,
            unit_price=price,
            labor_hours=labor_hours,
            labor_unit_price=labor_unit_price,
        )
    )
    print(f"  {ui.green('Added:')} {name} x{qty} {unit}")


def remove_line_item(estimate: Estimate) -> None:
    if not estimate.line_items:
        print("  No line items to remove.")
        return
    print_estimate(estimate, with_totals=False)
    choice = prompt_nonempty("Remove item #: ")
    try:
        idx = int(choice) - 1
        removed = estimate.line_items.pop(idx)
        print(f"  Removed: {removed.description}")
    except (ValueError, IndexError):
        print("  Invalid selection.")


def edit_line_item(estimate: Estimate) -> None:
    if not estimate.line_items:
        print("  No line items to edit.")
        return
    print_estimate(estimate, with_totals=False)
    choice = prompt_nonempty("Edit item #: ")
    try:
        idx = int(choice) - 1
        li = estimate.line_items[idx]
    except (ValueError, IndexError):
        print("  Invalid selection.")
        return
    li.description = prompt_nonempty(f"  Description [{li.description}]: ", default=li.description)
    li.quantity = prompt_float(f"  Quantity [{li.quantity}]: ", default=li.quantity)
    li.unit = prompt_nonempty(f"  Unit [{li.unit}]: ", default=li.unit)
    li.unit_price = prompt_float(f"  Unit price [{li.unit_price}]: ", default=li.unit_price)
    li.labor_hours = prompt_float(f"  Labor hours [{li.labor_hours}]: ", default=li.labor_hours)
    print(f"  Updated: {li.description}")


def print_estimate(estimate: Estimate, with_totals: bool = True) -> None:
    print()
    print(ui.banner(estimate.title))
    if not estimate.line_items:
        print(ui.dim("  (no line items yet)"))
    else:
        print(ui.bold(f"  {'#':>3}  {'Description':<30}{'Qty':>8} {'Unit':<5}{'$/Unit':>9}{'Line $':>11}"))
        print("  " + ui.rule(64))
        for i, li in enumerate(estimate.line_items, start=1):
            line_total = li.line_total(estimate.labor_rate_per_hour)
            print(f"  {i:>3}  {li.description:<30}{li.quantity:>8.2f} {li.unit:<5}{li.unit_price:>9.2f}{line_total:>11.2f}")
            if li.labor_hours:
                print(ui.dim(f"        + {li.labor_hours:.2f} hr labor @ ${estimate.labor_rate_per_hour:.2f}/hr"))
    if with_totals:
        print("  " + ui.rule(64))
        print(f"  {'Materials subtotal':<30}{ui.dim(f'${estimate.materials_subtotal:>10.2f}')}")
        if estimate.markup_percent:
            print(f"  {'Markup (' + str(estimate.markup_percent) + '%)':<30}{ui.yellow(f'${estimate.markup_amount:>10.2f}')}")
        print(f"  {'Labor subtotal':<30}{ui.dim(f'${estimate.labor_subtotal:>10.2f}')}")
        print(f"  {'Subtotal':<30}${estimate.subtotal:>10.2f}")
        print(f"  {'Tax (' + str(estimate.tax_rate_percent) + '%)':<30}{ui.dim(f'${estimate.tax:>10.2f}')}")
        print(ui.bold_green(f"  {'TOTAL':<30}${estimate.total:>10.2f}"))


def estimate_menu(estimate: Estimate, pricebook: dict) -> None:
    while True:
        print_estimate(estimate)
        print()
        print(ui.menu_line(("a", "Add item"), ("m", "Edit item"), ("r", "Remove item"), ("k", "Set markup %")))
        print(ui.menu_line(("s", "Save"), ("e", "Export .txt"), ("c", "Export .csv"), ("b", "Back to main menu")))
        choice = input(ui.bold("Choice: ")).strip().lower()
        if choice == "a":
            add_line_item(estimate, pricebook)
        elif choice == "m":
            edit_line_item(estimate)
        elif choice == "r":
            remove_line_item(estimate)
        elif choice == "k":
            estimate.markup_percent = prompt_float(
                f"Markup % on materials [{estimate.markup_percent}]: ", default=estimate.markup_percent
            )
        elif choice == "s":
            path = storage.save_estimate(estimate)
            print(f"  {ui.green('Saved to')} {path}")
        elif choice == "e":
            path = storage.export_text_report(estimate)
            print(f"  {ui.green('Report exported to')} {path}")
        elif choice == "c":
            path = storage.export_csv_report(estimate)
            print(f"  {ui.green('CSV exported to')} {path}")
        elif choice == "b":
            return
        else:
            print("  Unknown option.")


def new_estimate(pricebook: dict) -> Estimate:
    title = prompt_nonempty("Estimate / job title: ")
    labor_rate = prompt_float(
        f"Labor rate per hour [{pricebook.get('labor_rate_per_hour', 65.0):.2f}]: ",
        default=pricebook.get("labor_rate_per_hour", 65.0),
    )
    tax_rate = prompt_float(
        f"Tax rate % [{pricebook.get('tax_rate_percent', 0.0)}]: ",
        default=pricebook.get("tax_rate_percent", 0.0),
    )
    markup = prompt_float(
        f"Markup % on materials [{pricebook.get('markup_percent', 0.0)}]: ",
        default=pricebook.get("markup_percent", 0.0),
    )
    return Estimate(
        title=title, labor_rate_per_hour=labor_rate, tax_rate_percent=tax_rate, markup_percent=markup
    )


def load_estimate_menu() -> Estimate | None:
    files = storage.list_saved_estimates()
    if not files:
        print("  No saved estimates found.")
        return None
    for i, f in enumerate(files, start=1):
        print(f"  {ui.bold_cyan(f'{i:>2}')}. {f}")
    choice = prompt_nonempty("Load which #: ")
    try:
        idx = int(choice) - 1
        return storage.load_estimate(files[idx])
    except (ValueError, IndexError):
        print("  Invalid selection.")
        return None


def manage_pricebook(pricebook: dict) -> None:
    while True:
        print(ui.banner("Price Book"))
        materials = storage.get_materials(pricebook)
        last_category = None
        for i, m in enumerate(materials, start=1):
            if m.category != last_category:
                print(ui.bold(ui.magenta(f"  --- {m.category} ---")))
                last_category = m.category
            installed = m.unit_price + m.labor_unit_price
            labor_note = ui.dim(f" (incl. ${m.labor_unit_price:.2f} labor)") if m.labor_unit_price else ""
            print(f"  {ui.bold_cyan(f'{i:>2}')}. {m.name:<30} {installed:>8.2f} / {m.unit}{labor_note}")
        print()
        print(ui.menu_line(("a", "Add material"), ("u", "Update a material price"), ("b", "Back")))
        choice = input(ui.bold("Choice: ")).strip().lower()
        if choice == "a":
            name = prompt_nonempty("  Name: ")
            category = prompt_nonempty("  Category (Devices/Boxes/Wire & Cable/Conduit/Breakers/Panels/Lighting & Fixtures/Grounding/Misc): ", default="Other")
            unit = prompt_nonempty("  Unit: ", default="ea")
            price = prompt_float("  Material unit price: $")
            labor_unit_price = prompt_float(
                "  Labor $/unit already included, e.g. installed price (0 if none): $", default=0.0
            )
            pricebook.setdefault("materials", []).append(
                {"name": name, "category": category, "unit": unit, "unit_price": price, "labor_unit_price": labor_unit_price}
            )
            storage.save_pricebook(pricebook)
            print("  Saved to pricebook.")
        elif choice == "u":
            if not materials:
                print("  No materials in pricebook.")
                continue
            selected = prompt_nonempty("  Material # to search: ")
            try:
                material = pricebook["materials"][int(selected) - 1]
            except (ValueError, IndexError):
                print("  Invalid selection.")
                continue
            query = material.get("search_query") or material["name"]
            location = prompt_nonempty("  Search location [Maryland, United States]: ", default="Maryland, United States")
            try:
                offers = material_prices.search_material_prices(query, location)
            except material_prices.PriceLookupError as exc:
                print(f"  Price lookup failed: {exc}")
                continue
            if not offers:
                print("  No priced listings were returned.")
                continue
            print("  Verify the product and package/unit match before applying a listed price:")
            for i, offer in enumerate(offers, start=1):
                print(f"  {i:>2}. ${offer['price']:.2f} — {offer['source']}: {offer['title']}")
                if offer["url"]:
                    print(f"      {offer['url']}")
            selection = prompt_nonempty("  Apply offer # (blank cancels): ", default="")
            try:
                offer = offers[int(selection) - 1]
            except (ValueError, IndexError):
                print("  No price applied.")
                continue
            material["unit_price"] = offer["price"]
            material["price_source"] = {
                "provider": "Google Shopping / SerpApi",
                "merchant": offer["source"],
                "title": offer["title"],
                "url": offer["url"],
                "price": offer["price"],
                "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "location": location,
            }
            storage.save_pricebook(pricebook)
            print(f"  Saved ${offer['price']:.2f}/{material.get('unit', 'ea')} from {offer['source']}.")
        elif choice == "b":
            return
        else:
            print("  Unknown option.")


def labor_rate_menu(pricebook: dict) -> None:
    """Compare labor rates from multiple sources and optionally apply one."""
    while True:
        state = pricebook.get("state", "Maryland")
        cmp = labor_rates.compare_rates(
            state, custom_sources=storage.get_labor_rate_sources(pricebook)
        )
        print()
        print(ui.banner("Labor Rate Sources"))
        print(ui.dim(f"  State basis: {state}   "
                     f"Burden x{cmp.burden_multiplier:.2f}   "
                     f"Overhead & profit {cmp.overhead_profit_pct:.0f}%"))
        print(ui.dim("  Wage sources are burdened to a billable rate; billing sources pass through."))
        print("  " + ui.rule(70))
        print(f"  {'Source':<42}{'Low':>9}{'Typical':>9}{'High':>9}")
        print("  " + ui.rule(70))
        for s in cmp.billable_sources:
            print(f"  {s.label[:41]:<42}{s.low:>9.2f}{s.typical:>9.2f}{s.high:>9.2f}")
        print("  " + ui.rule(70))
        print(f"  {ui.bold('Blended (median of typical)'):<42}"
              f"{cmp.low:>9.2f}{ui.bold_green(f'{cmp.typical:>9.2f}')}{cmp.high:>9.2f}")
        print()
        current = storage.get_labor_rate(pricebook)
        print(f"  Current pricebook rate: {ui.bold_cyan(f'${current:.2f}/hr')}")
        print(f"  Recommended (blended):  {ui.bold_green(f'${cmp.recommended:.2f}/hr')}")
        print()
        print(ui.menu_line(("a", "Apply recommended"), ("m", "Enter a rate manually"),
                           ("d", "Show source detail"), ("b", "Back")))
        choice = input(ui.bold("Choice: ")).strip().lower()
        if choice == "a":
            storage.set_labor_rate(pricebook, cmp.recommended)
            storage.save_pricebook(pricebook)
            print(f"  {ui.green('Saved labor rate')} ${cmp.recommended:.2f}/hr")
        elif choice == "m":
            rate = prompt_float(f"  Labor rate $/hr [{current:.2f}]: ", default=current)
            storage.set_labor_rate(pricebook, rate)
            storage.save_pricebook(pricebook)
            print(f"  {ui.green('Saved labor rate')} ${rate:.2f}/hr")
        elif choice == "d":
            print()
            for s in cmp.sources:
                print(f"  {ui.bold(s.label)}  ({s.as_of}, {s.kind})")
                print(ui.dim(f"      raw range ${s.low:.2f}-${s.high:.2f}/hr"))
                if s.note:
                    print(ui.dim(f"      {s.note}"))
                print(ui.dim(f"      {s.url}"))
            print()
            print(ui.dim("  These are planning benchmarks, not a quote. Confirm against your own payroll and market."))
        elif choice == "b":
            return
        else:
            print("  Unknown option.")


def nec_calculator(pricebook: dict) -> None:
    print(ui.banner("NEC Quick Calc"))
    sqft = prompt_float("Home square footage: ")
    circuit_amps = prompt_float("General lighting circuit breaker size, 15 or 20 [20]: ", default=20.0)
    try:
        result = nec.calculate(sqft, circuit_amps=circuit_amps)
    except ValueError as exc:
        print(f"  Invalid input: {exc}")
        return
    print()
    print(nec.format_report(result, pricebook))


def main() -> None:
    pricebook = storage.load_pricebook()
    print(ui.banner("⚡ The Judith Group Estimator"))
    while True:
        print()
        print(ui.menu_line(("n", "New estimate"), ("l", "Load estimate"), ("p", "Price book"), ("r", "Labor rates"), ("c", "NEC quick calc"), ("q", "Quit")))
        choice = input(ui.bold("Choice: ")).strip().lower()
        if choice == "n":
            estimate = new_estimate(pricebook)
            estimate_menu(estimate, pricebook)
        elif choice == "l":
            estimate = load_estimate_menu()
            if estimate:
                estimate_menu(estimate, pricebook)
        elif choice == "p":
            manage_pricebook(pricebook)
        elif choice == "r":
            labor_rate_menu(pricebook)
        elif choice == "c":
            nec_calculator(pricebook)
        elif choice == "q":
            print(ui.bold_cyan("Goodbye."))
            return
        else:
            print("  Unknown option.")


if __name__ == "__main__":
    main()
