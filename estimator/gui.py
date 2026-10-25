"""Clickable desktop UI for the electrical work estimator (Tkinter, stdlib only).

Tkinter ships with the Python standard library on Windows and macOS. On some
Linux distributions (Debian/Ubuntu) it's split into a separate OS package —
if this fails to import, run: `sudo apt install python3-tk` (or your distro's
equivalent), or use the text-based interface via `python3 main.py --cli`.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from datetime import datetime
import threading
import webbrowser

from .models import Estimate, LineItem
from . import material_prices, nec, pdf_import, storage

APP_TITLE = "The Judith Group Estimator"
US_STATES = (
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "District of Columbia",
)
CODE_EDITIONS = ("Select / confirm with AHJ", "2017 NEC", "2020 NEC", "2023 NEC", "2026 NEC", "Other / local code")
MARYLAND_CODE_EDITION = "2020 NEC (Maryland baseline; confirm local amendments)"


def _default_code_edition(state: str) -> str:
    return MARYLAND_CODE_EDITION if state == "Maryland" else "Select / confirm with AHJ"


def _parse_float(value: str) -> float:
    return float(value.strip())


def _configure_styles(root: tk.Misc) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    root.configure(background="#f3f6fa")
    style.configure("TFrame", background="#f3f6fa")
    style.configure("Surface.TFrame", background="#ffffff")
    style.configure("TLabel", background="#f3f6fa", foreground="#243247", font=("TkDefaultFont", 10))
    style.configure("Title.TLabel", background="#ffffff", foreground="#132238", font=("TkDefaultFont", 20, "bold"))
    style.configure("Subtitle.TLabel", background="#ffffff", foreground="#5b6b80", font=("TkDefaultFont", 10))
    style.configure("Section.TLabel", background="#f3f6fa", foreground="#34465e", font=("TkDefaultFont", 11, "bold"))
    style.configure("TButton", padding=(12, 8), font=("TkDefaultFont", 10))
    style.configure("Primary.TButton", background="#1457a6", foreground="#ffffff", padding=(14, 10), font=("TkDefaultFont", 10, "bold"))
    style.map("Primary.TButton", background=[("active", "#0f478b"), ("pressed", "#0b3971")], foreground=[("disabled", "#d7e1ed")])
    style.configure("TEntry", padding=6, fieldbackground="#ffffff")
    style.configure("TCombobox", padding=5, fieldbackground="#ffffff")
    style.configure("TLabelframe", background="#f3f6fa", bordercolor="#d8e0ea", relief="solid")
    style.configure("TLabelframe.Label", background="#f3f6fa", foreground="#243247", font=("TkDefaultFont", 10, "bold"))
    style.configure("Treeview", background="#ffffff", fieldbackground="#ffffff", foreground="#243247", rowheight=28, bordercolor="#d8e0ea")
    style.configure("Treeview.Heading", background="#eaf0f7", foreground="#243247", font=("TkDefaultFont", 9, "bold"), padding=(8, 7))
    style.map("Treeview", background=[("selected", "#d8e9fb")], foreground=[("selected", "#132238")])


class NewEstimateDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, pricebook: dict):
        super().__init__(parent)
        self.title("Create estimate")
        self.resizable(False, False)
        self.result: Estimate | None = None

        frm = ttk.Frame(self, padding=22)
        frm.grid(row=0, column=0, sticky="nsew")

        self.title_var = tk.StringVar()
        self.labor_rate_var = tk.StringVar(value=str(pricebook.get("labor_rate_per_hour", 65.0)))
        self.tax_var = tk.StringVar(value=str(pricebook.get("tax_rate_percent", 0.0)))
        self.markup_var = tk.StringVar(value=str(pricebook.get("markup_percent", 0.0)))
        self.state_var = tk.StringVar(value="Maryland")
        self.locality_var = tk.StringVar()
        self.code_edition_var = tk.StringVar(value=MARYLAND_CODE_EDITION)

        ttk.Label(frm, text="Job / estimate title:").grid(row=0, column=0, sticky="w", pady=(0, 5))
        ttk.Entry(frm, textvariable=self.title_var, width=48).grid(row=0, column=1, sticky="ew", pady=(0, 5), padx=(12, 0))

        settings = ttk.LabelFrame(frm, text="Estimate settings", padding=(12, 8))
        settings.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 10))
        settings.columnconfigure(1, weight=1)
        for i, (label, var) in enumerate((
            ("Labor rate ($/hr)", self.labor_rate_var),
            ("Tax rate (%)", self.tax_var),
            ("Markup on materials (%)", self.markup_var),
        )):
            ttk.Label(settings, text=label).grid(row=i, column=0, sticky="w", pady=4)
            ttk.Entry(settings, textvariable=var, width=16).grid(row=i, column=1, sticky="w", pady=4, padx=(12, 0))

        location = ttk.LabelFrame(frm, text="Project location and code reference", padding=(12, 8))
        location.grid(row=2, column=0, columnspan=2, sticky="ew")
        location.columnconfigure(1, weight=1)
        ttk.Label(location, text="State").grid(row=0, column=0, sticky="w", pady=4)
        state_combo = ttk.Combobox(location, textvariable=self.state_var, values=US_STATES, state="readonly", width=30)
        state_combo.grid(row=0, column=1, sticky="ew", pady=4, padx=(12, 0))
        state_combo.bind("<<ComboboxSelected>>", self._state_changed)
        ttk.Label(location, text="County / city (AHJ)").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(location, textvariable=self.locality_var, width=34).grid(row=1, column=1, sticky="ew", pady=4, padx=(12, 0))
        ttk.Label(location, text="Code edition (reference only)").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Combobox(location, textvariable=self.code_edition_var, values=CODE_EDITIONS + (MARYLAND_CODE_EDITION,), width=46).grid(
            row=2, column=1, sticky="ew", pady=4, padx=(12, 0))
        ttk.Label(location, text="Confirm adopted edition and local amendments with the AHJ.",
                  wraplength=420, style="Subtitle.TLabel").grid(row=3, column=0, columnspan=2, sticky="w", pady=(5, 0))
        frm.columnconfigure(1, weight=1)

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=2, pady=(16, 0), sticky="e")
        ttk.Button(btns, text="Create", command=self._on_ok).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left")

        self.bind("<Return>", lambda e: self._on_ok())
        self.transient(parent)
        self.grab_set()
        frm.winfo_children()[1].focus_set()

    def _state_changed(self, event: object = None) -> None:
        self.code_edition_var.set(_default_code_edition(self.state_var.get()))

    def _on_ok(self) -> None:
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror("Missing title", "Please enter a job/estimate title.", parent=self)
            return
        try:
            labor_rate = _parse_float(self.labor_rate_var.get())
            tax = _parse_float(self.tax_var.get())
            markup = _parse_float(self.markup_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Labor rate, tax, and markup must be numbers.", parent=self)
            return
        self.result = Estimate(
            title=title, labor_rate_per_hour=labor_rate, tax_rate_percent=tax, markup_percent=markup,
            state=self.state_var.get(), local_jurisdiction=self.locality_var.get().strip(),
            code_edition=self.code_edition_var.get().strip() or _default_code_edition(self.state_var.get()),
        )
        self.destroy()


class LoadEstimateDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc):
        super().__init__(parent)
        self.title("Open saved estimate")
        self.resizable(False, False)
        self.result: str | None = None

        frm = ttk.Frame(self, padding=16)
        frm.grid(row=0, column=0)

        files = storage.list_saved_estimates()
        ttk.Label(frm, text="Saved estimates:").grid(row=0, column=0, sticky="w")
        self.listbox = tk.Listbox(frm, width=40, height=10)
        for f in files:
            self.listbox.insert("end", f)
        self.listbox.grid(row=1, column=0, pady=8)
        if files:
            self.listbox.selection_set(0)
        self.listbox.bind("<Double-1>", lambda e: self._on_ok())

        btns = ttk.Frame(frm)
        btns.grid(row=2, column=0, sticky="e")
        ttk.Button(btns, text="Load", command=self._on_ok).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left")

        self.transient(parent)
        self.grab_set()

    def _on_ok(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Load Estimate", "Select a saved estimate first.", parent=self)
            return
        self.result = self.listbox.get(sel[0])
        self.destroy()


class PdfImportReviewDialog(tk.Toplevel):
    """Show the extracted quantity rows before opening the editable estimate."""

    def __init__(self, parent: tk.Misc, estimate: Estimate, matched_count: int):
        super().__init__(parent)
        self.title("Review PDF import")
        self.geometry("720x440")
        self.minsize(600, 340)
        self.result = False

        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=f"Draft estimate: {estimate.title}", font=("TkDefaultFont", 13, "bold")).pack(anchor="w")
        ttk.Label(
            frm,
            text=(f"Found {len(estimate.line_items)} item(s); {matched_count} matched to your price book. "
                  "Unmatched items start at $0. Review every quantity and price before using this estimate. "
                  "Scanned drawings and counts inferred from plan geometry are not supported."),
            wraplength=660,
        ).pack(anchor="w", pady=(6, 10))

        table = ttk.Treeview(frm, columns=("qty", "unit", "price", "labor"), show="tree headings", height=10)
        table.heading("#0", text="Description")
        table.heading("qty", text="Qty")
        table.heading("unit", text="Unit")
        table.heading("price", text="Material $/unit")
        table.heading("labor", text="Labor $/unit")
        table.column("#0", width=340)
        table.column("qty", width=70, anchor="e")
        table.column("unit", width=65, anchor="center")
        table.column("price", width=105, anchor="e")
        table.column("labor", width=105, anchor="e")
        table.pack(fill="both", expand=True)
        for item in estimate.line_items:
            table.insert(
                "", "end", text=item.description,
                values=(f"{item.quantity:g}", item.unit, f"${item.unit_price:.2f}", f"${item.labor_unit_price:.2f}"),
            )

        buttons = ttk.Frame(frm)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Create estimate", style="Primary.TButton", command=self._accept).pack(side="right", padx=(6, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right")
        self.transient(parent)
        self.grab_set()

    def _accept(self) -> None:
        self.result = True
        self.destroy()


class AddItemDialog(tk.Toplevel):
    """Add a line item, either picked from the categorized price book or as a custom entry."""

    def __init__(self, parent: tk.Misc, pricebook: dict):
        super().__init__(parent)
        self.title("Add Line Item")
        self.resizable(False, False)
        self.pricebook = pricebook
        self.result: LineItem | None = None
        self._materials: list = []

        frm = ttk.Frame(self, padding=16)
        frm.grid(row=0, column=0)

        categories = storage.get_categories(pricebook) + ["Custom"]
        self.category_var = tk.StringVar(value=categories[0])
        self.material_var = tk.StringVar()
        self.qty_var = tk.StringVar(value="1")
        self.labor_hours_var = tk.StringVar(value="0")
        self.custom_name_var = tk.StringVar()
        self.custom_unit_var = tk.StringVar(value="ea")
        self.custom_price_var = tk.StringVar(value="0")
        self.custom_labor_unit_var = tk.StringVar(value="0")

        ttk.Label(frm, text="Category:").grid(row=0, column=0, sticky="w", pady=4)
        self.category_combo = ttk.Combobox(frm, textvariable=self.category_var, values=categories, state="readonly", width=30)
        self.category_combo.grid(row=0, column=1, pady=4, padx=(8, 0))
        self.category_combo.bind("<<ComboboxSelected>>", self._on_category_change)

        ttk.Label(frm, text="Material:").grid(row=1, column=0, sticky="w", pady=4)
        self.material_combo = ttk.Combobox(frm, textvariable=self.material_var, state="readonly", width=30)
        self.material_combo.grid(row=1, column=1, pady=4, padx=(8, 0))
        self.material_combo.bind("<<ComboboxSelected>>", self._on_material_change)

        self.name_label = ttk.Label(frm, text="Name:")
        self.name_entry = ttk.Entry(frm, textvariable=self.custom_name_var, width=32)
        self.unit_label = ttk.Label(frm, text="Unit:")
        self.unit_entry = ttk.Entry(frm, textvariable=self.custom_unit_var, width=10)
        self.price_label = ttk.Label(frm, text="Material $/unit:")
        self.price_entry = ttk.Entry(frm, textvariable=self.custom_price_var, width=10)
        self.labor_unit_label = ttk.Label(frm, text="Labor $/unit (0 to use hours instead):")
        self.labor_unit_entry = ttk.Entry(frm, textvariable=self.custom_labor_unit_var, width=10)

        ttk.Label(frm, text="Quantity:").grid(row=6, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.qty_var, width=10).grid(row=6, column=1, sticky="w", pady=4, padx=(8, 0))

        self.labor_hours_label = ttk.Label(frm, text="Labor hours (if not baked into unit price):")
        self.labor_hours_entry = ttk.Entry(frm, textvariable=self.labor_hours_var, width=10)
        self.labor_hours_label.grid(row=7, column=0, sticky="w", pady=4)
        self.labor_hours_entry.grid(row=7, column=1, sticky="w", pady=4, padx=(8, 0))

        self.info_var = tk.StringVar(value="")
        ttk.Label(frm, textvariable=self.info_var, foreground="#1a7d3a", wraplength=340).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        btns = ttk.Frame(frm)
        btns.grid(row=9, column=0, columnspan=2, pady=(12, 0), sticky="e")
        ttk.Button(btns, text="Add", command=self._on_ok).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left")

        self._on_category_change()
        self.transient(parent)
        self.grab_set()

    def _custom_widgets(self) -> list[tk.Widget]:
        return [
            self.name_label, self.name_entry,
            self.unit_label, self.unit_entry,
            self.price_label, self.price_entry,
            self.labor_unit_label, self.labor_unit_entry,
        ]

    def _on_category_change(self, event: object = None) -> None:
        is_custom = self.category_var.get() == "Custom"
        if is_custom:
            self.material_combo.grid_remove()
            self.info_var.set("")
            self.labor_hours_entry.configure(state="normal")
            rows = [(2, 0), (2, 1), (3, 0), (3, 1), (4, 0), (4, 1), (5, 0), (5, 1)]
            for widget, (r, c) in zip(self._custom_widgets(), rows):
                widget.grid(row=r, column=c, sticky="w", pady=4, padx=(8, 0) if c == 1 else 0)
        else:
            for widget in self._custom_widgets():
                widget.grid_remove()
            self.material_combo.grid()
            materials = storage.get_materials_by_category(self.pricebook, self.category_var.get())
            self._materials = materials
            self.material_combo["values"] = [m.name for m in materials]
            if materials:
                self.material_combo.current(0)
                self._on_material_change()

    def _on_material_change(self, event: object = None) -> None:
        idx = self.material_combo.current()
        if idx < 0 or idx >= len(self._materials):
            return
        m = self._materials[idx]
        installed = m.unit_price + m.labor_unit_price
        if m.labor_unit_price:
            self.info_var.set(f"${m.unit_price:.2f} material + ${m.labor_unit_price:.2f} labor = ${installed:.2f}/{m.unit} (labor included)")
            self.labor_hours_var.set("0")
            self.labor_hours_entry.configure(state="disabled")
        else:
            self.info_var.set(f"${m.unit_price:.2f}/{m.unit} material only — enter labor hours below")
            self.labor_hours_entry.configure(state="normal")

    def _on_ok(self) -> None:
        try:
            qty = _parse_float(self.qty_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Quantity must be a number.", parent=self)
            return

        if self.category_var.get() == "Custom":
            name = self.custom_name_var.get().strip()
            if not name:
                messagebox.showerror("Invalid input", "Name is required.", parent=self)
                return
            unit = self.custom_unit_var.get().strip() or "ea"
            try:
                price = _parse_float(self.custom_price_var.get())
                labor_unit_price = _parse_float(self.custom_labor_unit_var.get())
                labor_hours = _parse_float(self.labor_hours_var.get())
            except ValueError:
                messagebox.showerror("Invalid input", "Price and labor fields must be numbers.", parent=self)
                return
        else:
            idx = self.material_combo.current()
            if idx < 0 or idx >= len(self._materials):
                messagebox.showerror("Invalid input", "Select a material.", parent=self)
                return
            m = self._materials[idx]
            name, unit, price, labor_unit_price = m.name, m.unit, m.unit_price, m.labor_unit_price
            try:
                labor_hours = 0.0 if labor_unit_price else _parse_float(self.labor_hours_var.get())
            except ValueError:
                messagebox.showerror("Invalid input", "Labor hours must be a number.", parent=self)
                return

        self.result = LineItem(
            description=name, quantity=qty, unit=unit, unit_price=price,
            labor_hours=labor_hours, labor_unit_price=labor_unit_price,
        )
        self.destroy()


class EditItemDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, line_item: LineItem):
        super().__init__(parent)
        self.title("Edit Line Item")
        self.resizable(False, False)
        self.result: LineItem | None = None

        frm = ttk.Frame(self, padding=16)
        frm.grid(row=0, column=0)

        self.desc_var = tk.StringVar(value=line_item.description)
        self.qty_var = tk.StringVar(value=str(line_item.quantity))
        self.unit_var = tk.StringVar(value=line_item.unit)
        self.price_var = tk.StringVar(value=str(line_item.unit_price))
        self.labor_hours_var = tk.StringVar(value=str(line_item.labor_hours))
        self.labor_unit_var = tk.StringVar(value=str(line_item.labor_unit_price))

        rows = [
            ("Description:", self.desc_var, 32),
            ("Quantity:", self.qty_var, 10),
            ("Unit:", self.unit_var, 10),
            ("Material $/unit:", self.price_var, 10),
            ("Labor hours:", self.labor_hours_var, 10),
            ("Labor $/unit (baked in):", self.labor_unit_var, 10),
        ]
        for i, (label, var, width) in enumerate(rows):
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky="w", pady=4)
            ttk.Entry(frm, textvariable=var, width=width).grid(row=i, column=1, pady=4, padx=(8, 0), sticky="w")

        btns = ttk.Frame(frm)
        btns.grid(row=len(rows), column=0, columnspan=2, pady=(12, 0), sticky="e")
        ttk.Button(btns, text="Save", command=self._on_ok).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left")

        self.transient(parent)
        self.grab_set()

    def _on_ok(self) -> None:
        desc = self.desc_var.get().strip()
        if not desc:
            messagebox.showerror("Invalid input", "Description is required.", parent=self)
            return
        try:
            qty = _parse_float(self.qty_var.get())
            price = _parse_float(self.price_var.get())
            labor_hours = _parse_float(self.labor_hours_var.get())
            labor_unit_price = _parse_float(self.labor_unit_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Quantity/price/labor fields must be numbers.", parent=self)
            return
        unit = self.unit_var.get().strip() or "ea"
        self.result = LineItem(
            description=desc, quantity=qty, unit=unit, unit_price=price,
            labor_hours=labor_hours, labor_unit_price=labor_unit_price,
        )
        self.destroy()


class EstimateWindow(tk.Toplevel):
    def __init__(self, parent: tk.Misc, estimate: Estimate, pricebook: dict):
        super().__init__(parent)
        self.estimate = estimate
        self.pricebook = pricebook
        self.title(f"{APP_TITLE} — {estimate.title}")
        self.geometry("1100x720")
        self.minsize(880, 600)

        top = ttk.Frame(self, padding=(16, 14, 16, 8))
        top.pack(fill="x")
        self.labor_rate_var = tk.StringVar(value=str(estimate.labor_rate_per_hour))
        self.tax_var = tk.StringVar(value=str(estimate.tax_rate_percent))
        self.markup_var = tk.StringVar(value=str(estimate.markup_percent))
        self.state_var = tk.StringVar(value=estimate.state)
        self.locality_var = tk.StringVar(value=estimate.local_jurisdiction)
        self.code_edition_var = tk.StringVar(value=estimate.code_edition)
        fields = [
            ("Labor $/hr:", self.labor_rate_var),
            ("Tax %:", self.tax_var),
            ("Markup %:", self.markup_var),
        ]
        for i, (label, var) in enumerate(fields):
            ttk.Label(top, text=label).grid(row=0, column=i * 2, sticky="w", padx=(0 if i == 0 else 12, 4))
            ttk.Entry(top, textvariable=var, width=8).grid(row=0, column=i * 2 + 1)
        ttk.Button(top, text="Apply", command=self._apply_fields).grid(row=0, column=6, padx=(12, 0))

        jurisdiction = ttk.LabelFrame(self, text="Project location and code reference", padding=(12, 10))
        jurisdiction.pack(fill="x", padx=14, pady=(2, 8))
        ttk.Label(jurisdiction, text="State:").grid(row=0, column=0, sticky="w")
        state_combo = ttk.Combobox(jurisdiction, textvariable=self.state_var, values=US_STATES, state="readonly", width=20)
        state_combo.grid(row=0, column=1, padx=(4, 12))
        state_combo.bind("<<ComboboxSelected>>", self._state_changed)
        ttk.Label(jurisdiction, text="County / city (AHJ):").grid(row=0, column=2, sticky="w")
        ttk.Entry(jurisdiction, textvariable=self.locality_var, width=20).grid(row=0, column=3, padx=4)
        ttk.Label(jurisdiction, text="Code edition (reference only):").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Combobox(jurisdiction, textvariable=self.code_edition_var,
                     values=CODE_EDITIONS + (MARYLAND_CODE_EDITION,), width=49).grid(
            row=1, column=1, columnspan=3, sticky="w", padx=(4, 0), pady=(4, 0))
        ttk.Label(jurisdiction, text="Confirm the adopted edition and local amendments with the AHJ.").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(4, 0))

        columns = ("qty", "unit", "unit_price", "labor", "line_total")
        self.tree = ttk.Treeview(self, columns=columns, show="tree headings", height=14)
        self.tree.heading("#0", text="Description")
        self.tree.heading("qty", text="Qty")
        self.tree.heading("unit", text="Unit")
        self.tree.heading("unit_price", text="$/Unit")
        self.tree.heading("labor", text="Labor")
        self.tree.heading("line_total", text="Line $")
        self.tree.column("#0", width=280)
        self.tree.column("qty", width=70, anchor="e")
        self.tree.column("unit", width=60, anchor="center")
        self.tree.column("unit_price", width=90, anchor="e")
        self.tree.column("labor", width=150, anchor="e")
        self.tree.column("line_total", width=100, anchor="e")
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=14, pady=8)
        self.tree.pack(in_=table_frame, side="left", fill="both", expand=True)
        tree_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        tree_scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.bind("<Double-1>", lambda e: self._edit_item())

        btns = ttk.Frame(self, padding=(12, 4))
        btns.pack(fill="x")
        ttk.Button(btns, text="Add Item", command=self._add_item).pack(side="left", padx=4)
        ttk.Button(btns, text="Edit Item", command=self._edit_item).pack(side="left", padx=4)
        ttk.Button(btns, text="Remove Item", command=self._remove_item).pack(side="left", padx=4)
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Export .txt", command=self._export_txt).pack(side="left", padx=4)
        ttk.Button(btns, text="Export .csv", command=self._export_csv).pack(side="left", padx=4)
        ttk.Button(btns, text="Close", command=self.destroy).pack(side="right", padx=4)

        totals_frame = ttk.Frame(self, padding=(16, 8, 16, 14))
        totals_frame.pack(fill="x")
        self.totals_var = tk.StringVar()
        ttk.Label(totals_frame, textvariable=self.totals_var, font=("TkDefaultFont", 11), justify="right").pack(anchor="e")

        self._refresh()

    def _apply_fields(self) -> None:
        try:
            self.estimate.labor_rate_per_hour = _parse_float(self.labor_rate_var.get())
            self.estimate.tax_rate_percent = _parse_float(self.tax_var.get())
            self.estimate.markup_percent = _parse_float(self.markup_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Labor rate, tax, and markup must be numbers.", parent=self)
            return
        self.estimate.state = self.state_var.get()
        self.estimate.local_jurisdiction = self.locality_var.get().strip()
        self.estimate.code_edition = self.code_edition_var.get().strip() or _default_code_edition(self.estimate.state)
        self._refresh()

    def _state_changed(self, event: object = None) -> None:
        self.code_edition_var.set(_default_code_edition(self.state_var.get()))

    def _refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for i, li in enumerate(self.estimate.line_items):
            line_total = li.line_total(self.estimate.labor_rate_per_hour)
            if li.labor_unit_price:
                labor_desc = f"${li.labor_unit_price:.2f}/unit"
            elif li.labor_hours:
                labor_desc = f"{li.labor_hours:.2f} hr"
            else:
                labor_desc = "—"
            self.tree.insert(
                "", "end", iid=str(i), text=li.description,
                values=(f"{li.quantity:.2f}", li.unit, f"{li.unit_price:.2f}", labor_desc, f"{line_total:.2f}"),
            )
        lines = [f"Materials subtotal:     ${self.estimate.materials_subtotal:,.2f}"]
        if self.estimate.markup_percent:
            lines.append(f"Markup ({self.estimate.markup_percent:g}%):        ${self.estimate.markup_amount:,.2f}")
        lines.append(f"Labor subtotal:         ${self.estimate.labor_subtotal:,.2f}")
        lines.append(f"Subtotal:               ${self.estimate.subtotal:,.2f}")
        lines.append(f"Tax ({self.estimate.tax_rate_percent:g}%):             ${self.estimate.tax:,.2f}")
        lines.append(f"TOTAL:                  ${self.estimate.total:,.2f}")
        self.totals_var.set("\n".join(lines))

    def _selected_index(self) -> int | None:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _add_item(self) -> None:
        dlg = AddItemDialog(self, self.pricebook)
        self.wait_window(dlg)
        if dlg.result:
            self.estimate.line_items.append(dlg.result)
            self._refresh()

    def _edit_item(self) -> None:
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo("Edit item", "Select an item first.", parent=self)
            return
        dlg = EditItemDialog(self, self.estimate.line_items[idx])
        self.wait_window(dlg)
        if dlg.result:
            self.estimate.line_items[idx] = dlg.result
            self._refresh()

    def _remove_item(self) -> None:
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo("Remove item", "Select an item first.", parent=self)
            return
        del self.estimate.line_items[idx]
        self._refresh()

    def _save(self) -> None:
        path = storage.save_estimate(self.estimate)
        messagebox.showinfo("Saved", f"Saved to:\n{path}", parent=self)

    def _export_txt(self) -> None:
        path = storage.export_text_report(self.estimate)
        messagebox.showinfo("Exported", f"Report exported to:\n{path}", parent=self)

    def _export_csv(self) -> None:
        path = storage.export_csv_report(self.estimate)
        messagebox.showinfo("Exported", f"CSV exported to:\n{path}", parent=self)


class PriceBookWindow(tk.Toplevel):
    def __init__(self, parent: tk.Misc, pricebook: dict):
        super().__init__(parent)
        self.pricebook = pricebook
        self.title(f"{APP_TITLE} — Price Book")
        self.geometry("900x680")
        self.minsize(760, 540)

        self.tree = ttk.Treeview(self, columns=("price", "labor"), show="tree headings", height=18)
        self.tree.heading("#0", text="Item")
        self.tree.heading("price", text="Material $/unit")
        self.tree.heading("labor", text="Labor $/unit")
        self.tree.column("#0", width=320)
        self.tree.column("price", width=120, anchor="e")
        self.tree.column("labor", width=120, anchor="e")
        lookup_frame = ttk.Frame(self, padding=(12, 8, 12, 0))
        lookup_frame.pack(fill="x")
        self.location_var = tk.StringVar(value="Maryland, United States")
        ttk.Label(lookup_frame, text="Search location:").pack(side="left")
        ttk.Entry(lookup_frame, textvariable=self.location_var, width=27).pack(side="left", padx=(6, 12))
        self.lookup_button = ttk.Button(lookup_frame, text="Find live prices for selected item", command=self._lookup_selected)
        self.lookup_button.pack(side="left")
        self.lookup_status = tk.StringVar(value="Uses Google Shopping via SerpApi; requires a configured API key.")
        ttk.Label(self, textvariable=self.lookup_status, wraplength=850).pack(anchor="w", padx=14, pady=(2, 4))
        self._material_rows: dict[str, dict] = {}

        catalog_frame = ttk.Frame(self, padding=(12, 12, 12, 8))
        catalog_frame.pack(fill="both", expand=True)
        self.tree.pack(in_=catalog_frame, side="left", fill="both", expand=True)
        catalog_scroll = ttk.Scrollbar(catalog_frame, orient="vertical", command=self.tree.yview)
        catalog_scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=catalog_scroll.set)

        add_frame = ttk.LabelFrame(self, text="Add material to price book", padding=(12, 10))
        add_frame.pack(fill="x", padx=12, pady=(0, 12))

        self.name_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.unit_var = tk.StringVar(value="ea")
        self.price_var = tk.StringVar(value="0")
        self.labor_unit_var = tk.StringVar(value="0")

        categories = storage.get_categories(pricebook)
        ttk.Label(add_frame, text="Name:").grid(row=0, column=0, sticky="w")
        ttk.Entry(add_frame, textvariable=self.name_var, width=26).grid(row=0, column=1, padx=4)
        ttk.Label(add_frame, text="Category:").grid(row=0, column=2, sticky="w")
        ttk.Combobox(add_frame, textvariable=self.category_var, values=categories, width=18).grid(row=0, column=3, padx=4)
        ttk.Label(add_frame, text="Unit:").grid(row=1, column=0, sticky="w")
        ttk.Entry(add_frame, textvariable=self.unit_var, width=10).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(add_frame, text="Material $:").grid(row=1, column=2, sticky="w")
        ttk.Entry(add_frame, textvariable=self.price_var, width=10).grid(row=1, column=3, sticky="w", padx=4)
        ttk.Label(add_frame, text="Labor $ (baked in):").grid(row=2, column=0, sticky="w")
        ttk.Entry(add_frame, textvariable=self.labor_unit_var, width=10).grid(row=2, column=1, sticky="w", padx=4)
        ttk.Button(add_frame, text="Add", command=self._add_material).grid(row=2, column=3, sticky="e")

        self._refresh()

    def _refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._material_rows.clear()
        for category in storage.get_categories(self.pricebook):
            node = self.tree.insert("", "end", text=category, open=True)
            for material in self.pricebook.get("materials", []):
                if material.get("category", "Other") != category:
                    continue
                iid = self.tree.insert(node, "end", text=material["name"], values=(
                    f"{float(material.get('unit_price', 0)):.2f}",
                    f"{float(material.get('labor_unit_price', 0)):.2f}",
                ))
                self._material_rows[iid] = material

    def _lookup_selected(self) -> None:
        selection = self.tree.selection()
        material = self._material_rows.get(selection[0]) if selection else None
        if material is None:
            messagebox.showinfo("Select a material", "Select a material row first.", parent=self)
            return
        query = material.get("search_query") or material["name"]
        location = self.location_var.get()
        self.lookup_button.configure(state="disabled")
        self.lookup_status.set(f"Searching merchant listings for {query!r}…")

        def lookup() -> None:
            try:
                offers = material_prices.search_material_prices(query, location)
                error = None
            except material_prices.PriceLookupError as exc:
                offers, error = [], str(exc)
            self.after(0, lambda: self._lookup_complete(material, offers, error, location))

        threading.Thread(target=lookup, daemon=True).start()

    def _lookup_complete(self, material: dict, offers: list[dict], error: str | None, location: str) -> None:
        self.lookup_button.configure(state="normal")
        if error:
            self.lookup_status.set("Price lookup failed.")
            messagebox.showerror("Price lookup failed", error, parent=self)
            return
        if not offers:
            self.lookup_status.set("No priced listings were returned.")
            messagebox.showinfo("No results", "The provider returned no listings with a usable price.", parent=self)
            return
        self._choose_offer(material, offers, location)

    def _choose_offer(self, material: dict, offers: list[dict], location: str) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Review live price offers")
        dialog.geometry("820x440")
        dialog.transient(self)
        ttk.Label(
            dialog,
            text=(f"Offers for {material['name']} ({material.get('unit', 'ea')}). Verify the exact specification "
                  "and that the listing is priced per this unit—not a spool, pack, or bulk quantity—before applying."),
            wraplength=780,
        ).pack(anchor="w", padx=12, pady=10)
        table = ttk.Treeview(dialog, columns=("merchant", "price"), show="tree headings", height=10)
        table.heading("#0", text="Listing")
        table.heading("merchant", text="Merchant")
        table.heading("price", text="Listed price")
        table.column("#0", width=480)
        table.column("merchant", width=180)
        table.column("price", width=100, anchor="e")
        table.pack(fill="both", expand=True, padx=12)
        for index, offer in enumerate(offers):
            table.insert("", "end", iid=str(index), text=offer["title"], values=(offer["source"], f"${offer['price']:.2f}"))
        if offers:
            table.selection_set("0")

        detail_var = tk.StringVar(value=offers[0]["url"])
        ttk.Label(dialog, textvariable=detail_var, wraplength=780).pack(anchor="w", padx=12, pady=6)

        def update_detail(event: object = None) -> None:
            chosen = table.selection()
            if chosen:
                detail_var.set(offers[int(chosen[0])]["url"] or "No product link provided")

        table.bind("<<TreeviewSelect>>", update_detail)
        buttons = ttk.Frame(dialog, padding=12)
        buttons.pack(fill="x")

        def open_listing() -> None:
            chosen = table.selection()
            if chosen and offers[int(chosen[0])]["url"]:
                webbrowser.open(offers[int(chosen[0])]["url"])

        def apply_offer() -> None:
            chosen = table.selection()
            if not chosen:
                return
            offer = offers[int(chosen[0])]
            material["unit_price"] = offer["price"]
            material["price_source"] = {
                "provider": "Google Shopping / SerpApi",
                "merchant": offer["source"],
                "title": offer["title"],
                "url": offer["url"],
                "price": offer["price"],
                "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "location": location.strip(),
            }
            storage.save_pricebook(self.pricebook)
            self.lookup_status.set(f"Saved selected offer from {offer['source']} at ${offer['price']:.2f}.")
            self._refresh()
            dialog.destroy()

        ttk.Button(buttons, text="Open listing", command=open_listing).pack(side="left")
        ttk.Button(buttons, text="Apply selected price", command=apply_offer).pack(side="right", padx=(6, 0))
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right")
        dialog.grab_set()

    def _add_material(self) -> None:
        name = self.name_var.get().strip()
        category = self.category_var.get().strip() or "Other"
        unit = self.unit_var.get().strip() or "ea"
        if not name:
            messagebox.showerror("Invalid input", "Name is required.", parent=self)
            return
        try:
            price = _parse_float(self.price_var.get())
            labor_unit_price = _parse_float(self.labor_unit_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Price fields must be numbers.", parent=self)
            return
        self.pricebook.setdefault("materials", []).append(
            {"name": name, "category": category, "unit": unit, "unit_price": price, "labor_unit_price": labor_unit_price}
        )
        storage.save_pricebook(self.pricebook)
        self.name_var.set("")
        self.price_var.set("0")
        self.labor_unit_var.set("0")
        self._refresh()


class NecCalcWindow(tk.Toplevel):
    def __init__(self, parent: tk.Misc):
        super().__init__(parent)
        self.title(f"{APP_TITLE} — NEC Quick Calc")
        self.geometry("860x760")
        self.minsize(760, 620)
        self.resizable(True, True)
        self.pricebook = parent.pricebook

        frm = ttk.Frame(self, padding=20)
        frm.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        frm.columnconfigure(0, weight=1)
        frm.rowconfigure(7, weight=1)

        self.sqft_var = tk.StringVar()
        self.amps_var = tk.StringVar(value="20")
        self.state_var = tk.StringVar(value="Maryland")
        self.locality_var = tk.StringVar()
        self.code_edition_var = tk.StringVar(value=MARYLAND_CODE_EDITION)
        ttk.Label(frm, text="Home square footage:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.sqft_var, width=12).grid(row=0, column=1, padx=(8, 0))
        ttk.Label(frm, text="Lighting circuit size (A):").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.amps_var, width=12).grid(row=1, column=1, padx=(8, 0))
        ttk.Label(frm, text="Project state:").grid(row=2, column=0, sticky="w", pady=4)
        state_combo = ttk.Combobox(frm, textvariable=self.state_var, values=US_STATES, state="readonly", width=28)
        state_combo.grid(row=2, column=1, padx=(8, 0), sticky="w")
        state_combo.bind("<<ComboboxSelected>>", self._state_changed)
        ttk.Label(frm, text="County / city (AHJ):").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.locality_var, width=30).grid(row=3, column=1, padx=(8, 0), sticky="w")
        ttk.Label(frm, text="Code edition (reference only):").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Combobox(frm, textvariable=self.code_edition_var, values=CODE_EDITIONS + (MARYLAND_CODE_EDITION,), width=48).grid(
            row=4, column=1, padx=(8, 0), sticky="w")
        ttk.Label(frm, text="Confirm local adoption and amendments with the AHJ.").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(2, 2))
        ttk.Button(frm, text="Calculate", command=self._calculate).grid(row=6, column=0, columnspan=2, pady=(8, 8))

        self.output = tk.Text(frm, width=72, height=25, wrap="none", state="disabled", font=("TkFixedFont",))
        scrollbar = ttk.Scrollbar(frm, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=scrollbar.set)
        self.output.grid(row=7, column=0, sticky="nsew", pady=(6, 0))
        scrollbar.grid(row=7, column=1, sticky="ns", pady=(6, 0))

    def _state_changed(self, event: object = None) -> None:
        self.code_edition_var.set(_default_code_edition(self.state_var.get()))

    def _calculate(self) -> None:
        try:
            sqft = _parse_float(self.sqft_var.get())
            amps = _parse_float(self.amps_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Square footage and circuit size must be numbers.", parent=self)
            return
        try:
            result = nec.calculate(sqft, circuit_amps=amps)
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc), parent=self)
            return
        locality = f", {self.locality_var.get().strip()}" if self.locality_var.get().strip() else ""
        basis = self.code_edition_var.get().strip() or _default_code_edition(self.state_var.get())
        report = (
            f"Project jurisdiction: {self.state_var.get()}{locality}\n"
            f"Selected code reference (calculation is not edition-adjusted): {basis}\n"
            "Confirm local adoption/amendments with the authority having jurisdiction.\n\n"
            + nec.format_report(result, self.pricebook)
        )
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", report)
        self.output.configure(state="disabled")


class MainWindow(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        _configure_styles(self)
        self.title(APP_TITLE)
        self.geometry("560x720")
        self.minsize(500, 660)
        self.resizable(True, True)
        self.pricebook = storage.load_pricebook()

        shell = ttk.Frame(self, padding=22)
        shell.pack(fill="both", expand=True)
        hero = ttk.Frame(shell, style="Surface.TFrame", padding=(24, 24, 24, 20))
        hero.pack(fill="x", pady=(0, 18))
        ttk.Label(hero, text="THE JUDITH GROUP", style="Subtitle.TLabel").pack(anchor="w")
        ttk.Label(hero, text="Electrical Estimator", style="Title.TLabel").pack(anchor="w", pady=(5, 4))
        ttk.Label(hero, text="Build estimates, review material pricing, and plan residential loads.",
                  style="Subtitle.TLabel", wraplength=450).pack(anchor="w")

        drop_panel = ttk.Frame(shell, style="Surface.TFrame", padding=(16, 12))
        drop_panel.pack(fill="x", pady=(0, 16))
        drop_title = ttk.Label(drop_panel, text="Drop a PDF takeoff here", style="Section.TLabel")
        drop_title.pack(anchor="w")
        drop_help = ttk.Label(
            drop_panel,
            text="Imports explicit item quantities from selectable PDF text. Scanned plans are not read.",
            style="Subtitle.TLabel", wraplength=440,
        )
        drop_help.pack(anchor="w", pady=(3, 8))
        ttk.Button(drop_panel, text="Choose PDF…", command=self._choose_pdf).pack(anchor="w")
        for target in (self, drop_panel, drop_title, drop_help):
            target.drop_target_register(DND_FILES)
            target.dnd_bind("<<Drop>>", self._on_pdf_drop)

        ttk.Label(shell, text="WORKSPACE", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        self._action(shell, "New estimate", "Start a job with labor, tax, and project code details.", self._new_estimate, primary=True)
        self._action(shell, "Open saved estimate", "Continue or export an existing job.", self._load_estimate)
        self._action(shell, "Price book", "Review material prices and labor allowances.", self._open_pricebook)
        self._action(shell, "NEC quick calculation", "Estimate dwelling load and a planning material takeoff.", self._open_nec)

        ttk.Label(shell, text="Project location and local code requirements should be confirmed with the AHJ.",
                  wraplength=460, foreground="#64748b").pack(anchor="w", pady=(14, 0))
        ttk.Button(shell, text="Quit", command=self.destroy).pack(anchor="e", pady=(10, 0))

    def _action(self, parent: ttk.Frame, title: str, description: str, command, primary: bool = False) -> None:
        card = ttk.Frame(parent, style="Surface.TFrame", padding=(14, 10))
        card.pack(fill="x", pady=5)
        ttk.Button(card, text=title, command=command,
                   style="Primary.TButton" if primary else "TButton", width=23).grid(row=0, column=0, rowspan=2, sticky="nsw")
        ttk.Label(card, text=description, style="Subtitle.TLabel", wraplength=270).grid(
            row=0, column=1, sticky="w", padx=(14, 4), pady=4)
        card.columnconfigure(1, weight=1)

    def _new_estimate(self) -> None:
        dlg = NewEstimateDialog(self, self.pricebook)
        self.wait_window(dlg)
        if dlg.result:
            EstimateWindow(self, dlg.result, self.pricebook)

    def _choose_pdf(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, title="Choose a PDF takeoff", filetypes=(("PDF files", "*.pdf"),),
        )
        if path:
            self._import_pdf(path)

    def _on_pdf_drop(self, event: object) -> None:
        paths = self.tk.splitlist(getattr(event, "data", ""))
        if not paths:
            return
        if len(paths) > 1:
            messagebox.showinfo("Import one PDF at a time", "Please drop one PDF file at a time.", parent=self)
            return
        self._import_pdf(paths[0])

    def _import_pdf(self, path: str) -> None:
        try:
            estimate, matched_count = pdf_import.create_estimate_from_pdf(path, self.pricebook)
        except (OSError, ValueError) as exc:
            messagebox.showerror("PDF import failed", str(exc), parent=self)
            return
        review = PdfImportReviewDialog(self, estimate, matched_count)
        self.wait_window(review)
        if review.result:
            EstimateWindow(self, estimate, self.pricebook)

    def _load_estimate(self) -> None:
        dlg = LoadEstimateDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            estimate = storage.load_estimate(dlg.result)
            EstimateWindow(self, estimate, self.pricebook)

    def _open_pricebook(self) -> None:
        PriceBookWindow(self, self.pricebook)

    def _open_nec(self) -> None:
        NecCalcWindow(self)


def main() -> None:
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
