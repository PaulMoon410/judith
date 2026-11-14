# Judith - Electrical estimating and job workspace

Build an estimate, review its assumptions, freeze a customer quote, reserve a crew,
and compare estimated costs against the completed job.

## Run the staff workspace

Python 3.10+ and the dependencies in `requirements.txt` are required.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# Set a unique password of at least 12 characters in your environment.
read -rs -p "Staff workspace password: " JUDITH_WORKSPACE_PASSWORD
export JUDITH_WORKSPACE_PASSWORD
.venv/bin/python -m estimator.workspace_web
```

Open <http://127.0.0.1:5000/workspace>. The staff API is **disabled** until the
password is configured. This is a shared-owner workspace, not a multi-tenant
application with individual employee accounts. Sessions last eight hours;
changing the password invalidates them. Sign-in is limited to ten attempts per
minute per client address. Do not put credentials in Git.

For production, use HTTPS and a persistent disk:

```sh
export JUDITH_SECURE_COOKIE=1
export JUDITH_JOBS_DB=/var/data/judith/jobs.sqlite3
.venv/bin/gunicorn 'estimator.workspace_web:create_app()' --bind 0.0.0.0:5000
```

On Render, use `pip install -r requirements.txt` as the build command, mount a
persistent disk at `/var/data`, set the variables above in the dashboard, and use
`gunicorn 'estimator.workspace_web:create_app()' --bind 0.0.0.0:$PORT` to run the
standalone staff app. SQLite requires a single service instance sharing that
disk; it is not suitable for multiple independent replicas.

The existing [customer Flask app](./app.py) also registers `/workspace`; its
`gunicorn app:app` / [Procfile](./Procfile) entrypoint remains unchanged.
Its customer form, pricing, labor reference, and NEC endpoints are preserved.
The [desktop estimator](./main.py), CLI (`python3 main.py --cli`), and legacy
Node/React prototypes are separate interfaces; `npm start` starts the legacy
Node app, **not** this workspace. Old estimate JSON files are not automatically
migrated or repriced.

## Daily workflow

1. **Start a draft.** Choose outlet replacement, recessed lighting, EV circuit,
   or panel replacement allowances; start blank; or import a text-based PDF
   quantity schedule. Save your own reviewed job as a reusable template.
2. **Review scope.** Enter the customer, site, assumptions, exclusions, and quote
   expiration. Site-specific design, AHJ rules, equipment compatibility, and
   omitted work still require qualified human review. EV and panel templates are
   deliberately incomplete planning allowances, not engineered installations.
3. **Verify materials.** Enter costs per base unit and record the supplier/quote,
   exact specification/SKU, and verification date. Use the package converter for
   rolls, sticks, or boxes. Missing prices or provenance and prices older than
   30 days block quoting. Explicitly mark zero-cost customer-supplied materials.
   Editing the unit, price, description, supplier, or specification in the UI
   clears the verification date.
4. **Review labor and pricing.** Enter person-hours per unit and your own fully
   burdened labor **cost**, not a retail billing benchmark. Review permits,
   equipment, other costs, waste, consumables, overhead, contingency, pricing
   method, and tax. Calculate an unsaved preview or explicitly save the draft.
5. **Quote and accept.** Resolve the quote checks and mark quoted to freeze its
   scope and totals. Print / save PDF without exposing internal labor costs,
   overhead, notes, or margins. Record customer acceptance after receiving it;
   this is not an e-signature service. Expired quotes cannot be newly accepted.
6. **Schedule.** Assign consistent crew names, start time, materials/permits ready
   date, travel, and buffer. Conflicting crew reservations are blocked unless
   the dispatcher provides an override reason. Release a reservation to return
   the job to accepted status.
7. **Learn from actuals.** Enter cumulative actual person-hours and direct costs.
   Compare cost and labor-hour variances before marking completed. Print a
   fixed-price invoice from the original agreed quote and export job costs as
   CSV. Invoices do not track payment or automatically bill actual overruns.

Quoted estimates cannot be edited in place. **Create revision** makes a new
linked draft while retaining the original quote and schedule. Reconfirm its
assumptions and obtain customer approval separately. Revisions do not cancel or
reschedule an existing job; release superseded reservations explicitly. Custom
templates omit customer, address, internal notes, and review confirmations.
Prices retain their original verification dates so old costs are flagged.

## Calculation rules

The workspace uses decimal arithmetic and half-up currency rounding, independently
of the unchanged legacy estimate model:

- Each material extension = quantity x unit cost x (1 + material waste %).
  Waste increases material purchasing, not installation hours.
- Consumables = percentage of extended materials. Labor = quantity x person-hours
  per unit x burdened hourly cost. Legacy per-unit installed labor charges are
  **not** added, preventing double-counting.
- Direct cost = materials + consumables + labor + permits + equipment + other.
- Overhead and contingency are each percentages of direct cost, rounded
  separately. Cost basis = direct cost + overhead + contingency.
- Markup: selling price = cost basis x (1 + markup %).
  Target margin: selling price = cost basis / (1 - margin %).
- Tax is selected explicitly: none, entire selling price, or materials' share
  of selling price (`selling price x materials including consumables / direct cost`).
  No jurisdictional tax treatment is inferred. Confirm this allocation with your
  accountant; unsupported tax rules require a separate calculation.
- Actual direct-cost variance = actual direct costs - estimated direct costs.
  Selling price less actual direct cost is **before overhead**, not net profit.
- Numeric inputs allow at most six fractional decimal places.

Scheduling reserves one continuous interval:
`estimated person-hours / crew size + elapsed travel + elapsed buffer`.
It rounds up to a minute and compares timezone-aware intervals transactionally,
including travel/buffer. It does not automatically skip nights, weekends, breaks,
holidays, or inspections, or model different crew skills/productivity. Review
duration, workday limits, travel, and readiness yourself; split work into visits
as needed. A single reservation cannot exceed 31 days.

## PDF and live-price limits

PDF import supports selectable text containing explicit material/quantity rows.
It does **not** infer geometry, perform OCR, or provide a verified drawing
takeoff. Imports are unreviewed drafts; unmatched materials remain unpriced,
explicit unit mismatches are not assigned a catalog price, and labor hours must
be entered manually. Maximum upload is 5 MB.

Optional supplier search uses the existing [SerpApi integration](./docs/material_price_api.md)
and `SERPAPI_KEY`. Results are candidates only; nothing is automatically applied
to the catalog or quote. Exact package size, delivered cost, compatibility,
availability, and product grade must be verified.

## Storage and backup

Jobs, frozen quotes, revisions, reusable templates, schedules, and cumulative
actuals are stored in `data/jobs.sqlite3`, or the absolute `JUDITH_JOBS_DB` path.
They are separate from the legacy transaction database and saved JSON estimates.
The starter catalog is read from [data/pricebook.json](./data/pricebook.json);
its existing prices are allowances, not newly verified supplier quotes.

Use SQLite's backup API or stop the app before copying the job database to a
secure backup location. Restore it to the same configured path. Runtime job
databases are ignored by Git. Keep backups off the application's ephemeral disk.

## Validation

```sh
.venv/bin/python -m unittest discover -s tests -v
node --check static/workspace.js
# Optional full browser workflow (requires the existing npm dependencies):
npm run test:workspace:browser
```

If Puppeteer's Chrome is missing, run `npx --no-install puppeteer browsers install chrome`.
The browser test starts and stops an isolated loopback server and temporary
database, and checks both desktop and mobile layouts. Set `JUDITH_TEST_PYTHON`
if your project interpreter is not `.venv/bin/python`.

Tests cover exact pricing, markup versus margin, tax allocation, legacy model
compatibility, PDF unit mismatches, persistent snapshots, concurrent edits and
crew reservations, revisions, actual-cost variance, and staff API protections.
