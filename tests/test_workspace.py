from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import io
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from estimator import jobs
from estimator.material_prices import PriceLookupError
from estimator.models import Estimate, LineItem
from estimator.pdf_import import parse_quantity_rows
from estimator.workspace_web import create_app
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def reviewed_job():
    job = jobs.new_job("Kitchen outlets")
    job.update(
        customer="Test Customer", address="10 Test Street", scope="Replace ten outlets.",
        labor_rate="10", permits="2", equipment="3", other_costs="4",
        consumables_percent="10", overhead_percent="10", contingency_percent="5",
        pricing_percent="25", tax_percent="6", tax_mode="all",
        tax_confirmed=True, labor_confirmed=True, scope_confirmed=True,
        items=[{
            "description": "Outlet", "unit": "ea", "quantity": "10", "unit_cost": ".105",
            "hours_per_unit": ".5", "waste_percent": "10", "supplier": "Supplier quote 123",
            "specification": "Brand / exact SKU", "verified_on": date.today().isoformat(),
            "customer_supplied": False,
        }],
    )
    return jobs.normalize_job(job)


class PricingTests(unittest.TestCase):
    def test_exact_decimal_costs_markup_and_tax(self):
        totals = jobs.calculate(reviewed_job())
        self.assertEqual(totals["rows"][0]["material"], "1.16")
        for key, expected in {
            "materials": "1.28", "labor": "50.00", "direct_cost": "60.28",
            "overhead": "6.03", "contingency": "3.01", "cost_basis": "69.32",
            "subtotal": "86.65", "tax": "5.20", "total": "91.85",
            "markup_percent": "25.00", "margin_percent": "20.00",
        }.items():
            with self.subTest(key=key):
                self.assertEqual(totals[key], expected)
        self.assertEqual(totals["warnings"], [])

    def test_margin_is_not_markup_and_material_tax_is_allocated(self):
        job = reviewed_job()
        job.update(pricing_mode="margin", tax_mode="materials")
        totals = jobs.calculate(job)
        self.assertEqual(totals["subtotal"], "92.43")
        self.assertEqual(totals["margin_percent"], "25.00")
        self.assertEqual(totals["taxable"], "1.96")
        self.assertEqual(totals["tax"], "0.12")
        job["tax_mode"] = "none"
        self.assertEqual(jobs.calculate(job)["tax"], "0.00")

    def test_review_checks_for_missing_stale_and_future_prices(self):
        job = reviewed_job()
        row = job["items"][0]
        row["verified_on"] = (date.today() - timedelta(days=31)).isoformat()
        self.assertIn("over 30 days", " ".join(jobs.calculate(job)["warnings"]))
        row.update(verified_on="", unit_cost="0")
        self.assertIn("price is missing", " ".join(jobs.calculate(job)["warnings"]))
        row["customer_supplied"] = True
        self.assertEqual(jobs.calculate(job)["warnings"], [])
        row.update(verified_on=(date.today() + timedelta(days=1)).isoformat())
        with self.assertRaises(jobs.JobError):
            jobs.normalize_job(job)

    def test_invalid_numbers_flags_and_margin_rejected(self):
        for value in ("NaN", "Infinity", "-1", True, None, "1e-999999999", "1.1234567"):
            with self.subTest(value=value), self.assertRaises(jobs.JobError):
                jobs.number(value, "cost")
        for update in ({"pricing_mode": "margin", "pricing_percent": "100"},
                       {"tax_confirmed": "false"}, {"items": {}}, {"valid_until": "tomorrow"}):
            with self.subTest(update=update), self.assertRaises(jobs.JobError):
                jobs.normalize_job({**reviewed_job(), **update})

    def test_legacy_estimate_calculations_and_round_trip_unchanged(self):
        estimate = Estimate("Legacy", 50, 6, markup_percent=10,
                            line_items=[LineItem("Wire", 10, "ft", 2, labor_hours=1, labor_unit_price=1)])
        self.assertEqual(estimate.total, 86.92)
        self.assertEqual(Estimate.from_dict(estimate.to_dict()).total, estimate.total)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / "jobs.db")
        self.store = jobs.JobStore(self.path)

    def accepted(self):
        job = self.store.create(reviewed_job())
        job = self.store.transition(job["id"], "quote", job["version"])
        return self.store.transition(job["id"], "accept", job["version"])

    def slot(self, job, **extra):
        return {"version": job["version"], "start": "2030-01-07T09:00:00-05:00",
                "crew": ["Paul", "Alex"], "ready_on": "2030-01-07",
                "travel_hours": ".5", "buffer_hours": ".25", **extra}

    def test_persistence_stale_updates_and_locked_quote_snapshots(self):
        job = self.store.create(reviewed_job())
        saved = self.store.update(job["id"], {**job, "title": "Changed"}, job["version"])
        with self.assertRaises(jobs.Conflict):
            self.store.update(job["id"], job, job["version"])
        quoted = self.store.transition(saved["id"], "quote", saved["version"])
        self.assertEqual(jobs.JobStore(self.path).get(job["id"]), quoted)
        with self.assertRaises(jobs.Conflict):
            self.store.update(quoted["id"], {**quoted, "labor_rate": "1"}, quoted["version"])
        revision = self.store.revise(quoted["id"])
        self.assertEqual(revision["source_id"], quoted["id"])
        self.assertEqual(revision["status"], "draft")
        self.assertFalse(revision["scope_confirmed"])
        self.assertEqual(self.store.get(quoted["id"])["quote_totals"]["total"], "91.85")

    def test_out_of_range_calculations_never_persist_an_unreadable_job(self):
        data = reviewed_job()
        data["items"][0].update(quantity="1000000", unit_cost="10000000")
        with self.assertRaises(jobs.JobError):
            self.store.create(data)
        self.assertEqual(self.store.list(), [])
        job = self.store.create(reviewed_job())
        with self.assertRaises(jobs.JobError):
            self.store.update(job["id"], data, job["version"])
        self.assertEqual(jobs.job_view(self.store.get(job["id"]))["totals"]["total"], "91.85")

    def test_quote_checks_cannot_be_bypassed_and_expired_quote_not_accepted(self):
        job = self.store.create({**reviewed_job(), "tax_confirmed": False})
        with self.assertRaises(jobs.JobError):
            self.store.transition(job["id"], "quote", job["version"])
        job = self.store.create(reviewed_job())
        quoted = self.store.transition(job["id"], "quote", job["version"])
        with patch("estimator.jobs.date") as clock:
            clock.fromisoformat = date.fromisoformat
            clock.today.return_value = date.today() + timedelta(days=31)
            with self.assertRaises(jobs.Conflict):
                self.store.transition(quoted["id"], "accept", quoted["version"])

    def test_duration_conflicts_overrides_and_adjacent_reservations(self):
        first = self.accepted()
        first = self.store.schedule(first["id"], self.slot(first))
        self.assertEqual(first["schedule"]["duration_minutes"], 195)
        self.assertEqual(first["schedule"]["end"], "2030-01-07T17:15:00+00:00")
        second = self.accepted()
        with self.assertRaises(jobs.Conflict):
            self.store.schedule(second["id"], self.slot(second, crew=["paul"]))
        with self.assertRaises(jobs.JobError):
            self.store.schedule(second["id"], self.slot(second, ready_on="2030-01-08"))
        with self.assertRaises(jobs.JobError):
            self.store.schedule(second["id"], self.slot(second, crew=["Paul", " paul "]))
        second = self.store.schedule(second["id"], self.slot(second, override_reason="Approved split assignment"))
        self.assertTrue(second["schedule"]["conflicts"])
        self.assertEqual(second["schedule"]["override_reason"], "Approved split assignment")
        third = self.accepted()
        third = self.store.schedule(third["id"], self.slot(third, start=first["schedule"]["end"]))
        self.assertFalse(third["schedule"]["conflicts"])

    def test_concurrent_scheduling_cannot_double_book(self):
        first, second = self.accepted(), self.accepted()

        def reserve(job):
            try:
                self.store.schedule(job["id"], self.slot(job))
                return "saved"
            except jobs.Conflict:
                return "conflict"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(reserve, (first, second)))
        self.assertCountEqual(outcomes, ["saved", "conflict"])

    def test_releasing_a_reservation_frees_crew_and_drafts_cannot_be_scheduled(self):
        first, second = self.accepted(), self.accepted()
        first = self.store.schedule(first["id"], self.slot(first))
        released = self.store.transition(first["id"], "unschedule", first["version"])
        self.assertIsNone(released["schedule"])
        self.assertEqual(released["status"], "accepted")
        self.store.schedule(second["id"], self.slot(second))
        draft = self.store.create(reviewed_job())
        with self.assertRaises(jobs.Conflict):
            self.store.schedule(draft["id"], self.slot(draft))

    def test_lifecycle_and_actual_cost_variance(self):
        job = self.accepted()
        with self.assertRaises(jobs.Conflict):
            self.store.transition(job["id"], "complete", job["version"])
        job = self.store.schedule(job["id"], self.slot(job))
        with self.assertRaises(jobs.JobError):
            self.store.transition(job["id"], "complete", job["version"])
        actual = {"version": job["version"], "labor_hours": "6", "labor_cost": "60",
                  "materials": "2", "permits": "2", "equipment": "3", "other_costs": "4"}
        job = self.store.actuals(job["id"], actual)
        comparison = jobs.job_view(job)["comparison"]
        self.assertEqual(comparison["actual_cost"], "71.00")
        self.assertEqual(comparison["direct_cost_variance"], "10.72")
        self.assertEqual(comparison["labor_hours_variance"], "1.0")
        completed = self.store.transition(job["id"], "complete", job["version"])
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["quote_totals"]["total"], "91.85")

    def test_custom_template_strips_customer_and_review_confirmations(self):
        job = self.store.create(reviewed_job())
        template = self.store.save_template(job["id"], "My outlets")
        self.assertEqual(self.store.templates()[0], template)
        self.assertEqual(template["job"]["customer"], "")
        self.assertEqual(template["job"]["address"], "")
        self.assertFalse(template["job"]["labor_confirmed"])
        self.assertEqual(template["job"]["items"], job["items"])


class PdfImportTests(unittest.TestCase):
    def test_mismatched_units_remain_unpriced_and_are_not_merged(self):
        pricebook = {"materials": [{"name": "Cable", "unit": "ft", "unit_price": 1}]}
        rows, matches = parse_quantity_rows("2 roll Cable\n10 ft Cable", pricebook)
        self.assertEqual([(row.quantity, row.unit, row.unit_price) for row in rows],
                         [(2, "roll", 0), (10, "ft", 1)])
        self.assertEqual(matches, 1)


class WorkspaceApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / "jobs.db")
        self.app = create_app({"TESTING": True, "JUDITH_JOBS_DB": self.path,
                               "JUDITH_WORKSPACE_PASSWORD": "workspace-test-password"})
        self.client = self.app.test_client()
        self.headers = {"X-Judith-Request": "workspace"}

    def login(self):
        response = self.client.post("/workspace/api/login", json={"password": "workspace-test-password"},
                                    headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.headers["X-CSRF-Token"] = response.json["csrf"]

    def test_authentication_csrf_logout_and_disabled_configuration(self):
        self.assertEqual(self.client.get("/workspace/api/jobs").status_code, 401)
        self.assertEqual(self.client.post("/workspace/api/login", json={"password": "wrong"},
                                         headers=self.headers).status_code, 401)
        self.login()
        self.assertEqual(self.client.get("/workspace/api/jobs").status_code, 200)
        self.assertEqual(self.client.post("/workspace/api/jobs", json={}, headers={
            "X-Judith-Request": "workspace"}).status_code, 403)
        self.assertEqual(self.client.post("/workspace/api/jobs", json={}, headers={
            **self.headers, "Origin": "https://other.invalid"}).status_code, 403)
        self.assertEqual(self.client.post("/workspace/api/logout", json={}, headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get("/workspace/api/jobs").status_code, 401)
        self.app.config["JUDITH_WORKSPACE_PASSWORD"] = ""
        self.assertEqual(self.client.get("/workspace/api/jobs").status_code, 503)

    def test_templates_update_preview_and_frozen_lifecycle(self):
        self.login()
        templates = self.client.get("/workspace/api/templates").json
        self.assertEqual(len(templates), 4)
        for template in templates:
            self.assertTrue(jobs.calculate(template["job"])["warnings"])
        response = self.client.post("/workspace/api/jobs", json={"template_id": "outlet"}, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        job = response.json
        path = "/workspace/api/jobs/" + job["id"]
        response = self.client.put(path, json={**reviewed_job(), "version": job["version"]}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        job = response.json
        preview = self.client.post("/workspace/api/preview", json={**reviewed_job(), "labor_rate": "20"}, headers=self.headers)
        self.assertNotEqual(preview.json["total"], job["totals"]["total"])
        self.assertEqual(self.client.get(path).json["totals"]["total"], "91.85")
        for action in ("quote", "accept"):
            response = self.client.post(path + "/action", json={"action": action, "version": job["version"]}, headers=self.headers)
            self.assertEqual(response.status_code, 200, response.json)
            job = response.json
        self.assertEqual(job["status"], "accepted")
        stale = self.client.put(path, json={**reviewed_job(), "version": job["version"]}, headers=self.headers)
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(self.client.get("/workspace/api/jobs").headers["Cache-Control"], "no-store")

    def test_login_throttle_persists_across_app_instances_and_expires(self):
        for _ in range(10):
            response = self.client.post("/workspace/api/login", json={"password": "wrong"}, headers=self.headers)
            self.assertEqual(response.status_code, 401)
        another = create_app(self.app.config).test_client()
        response = another.post("/workspace/api/login", json={"password": "workspace-test-password"}, headers=self.headers)
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response.headers)
        with patch("estimator.workspace_web.time.time", return_value=time.time() + 61):
            self.login()

    def test_valid_pdf_creates_unreviewed_draft_and_export_preserves_actuals(self):
        self.login()
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 50 700 Td (2 ea Duplex Outlet 15A) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
        pdf = io.BytesIO()
        writer.write(pdf)
        pdf.seek(0)
        response = self.client.post("/workspace/api/import-pdf",
                                    data={"file": (pdf, "outlets.pdf")}, headers=self.headers)
        self.assertEqual(response.status_code, 201, response.json)
        self.assertEqual(response.json["items"][0]["quantity"], "2.0")
        self.assertEqual(response.json["items"][0]["hours_per_unit"], "0")
        self.assertTrue(response.json["totals"]["warnings"])
        store = jobs.JobStore(self.path)
        data = reviewed_job()
        data["title"] = "=UNTRUSTED()"
        job = store.create(data)
        job = store.transition(job["id"], "quote", job["version"])
        job = store.transition(job["id"], "accept", job["version"])
        store.actuals(job["id"], {"version": job["version"], "labor_hours": "0", "labor_cost": "0",
                                 "materials": "0", "permits": "0", "equipment": "0", "other_costs": "0"})
        response = self.client.get("/workspace/api/export")
        self.assertEqual(response.status_code, 200)
        exported = response.get_data(as_text=True)
        self.assertIn("'=UNTRUSTED()", exported)
        self.assertIn("0,0.00,-60.28", exported)

    def test_invalid_payloads_and_provider_failures_are_explicit(self):
        self.login()
        for payload in ([], None, {"template_id": "missing"}):
            response = self.client.post("/workspace/api/jobs", json=payload, headers=self.headers)
            self.assertIn(response.status_code, (400, 404, 415))
        with patch("estimator.workspace_web.material_prices.search_material_prices",
                   side_effect=PriceLookupError("Provider unavailable")):
            response = self.client.post("/workspace/api/price-search", json={"query": "wire"}, headers=self.headers)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["error"], "Provider unavailable")
        response = self.client.post("/workspace/api/import-pdf",
                                    data={"file": (io.BytesIO(b"not a pdf"), "bad.pdf")}, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/workspace/api/jobs").json, [])


if __name__ == "__main__":
    unittest.main()
