"""Authenticated staff workspace; usable alone or alongside the customer app."""
from __future__ import annotations

from datetime import date, timedelta
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
import time

from flask import Blueprint, Flask, Response, current_app, g, jsonify, redirect, render_template, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, UnsupportedMediaType

from . import jobs, material_prices

ROOT = Path(__file__).resolve().parent.parent
COOKIE = "judith_workspace"
workspace = Blueprint("workspace", __name__, url_prefix="/workspace",
                      template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"),
                      static_url_path="/static")


def store() -> jobs.JobStore:
    return jobs.JobStore(current_app.config.get(
        "JUDITH_JOBS_DB", os.environ.get("JUDITH_JOBS_DB", str(ROOT / "data" / "jobs.sqlite3"))))


def password() -> str:
    return current_app.config.get("JUDITH_WORKSPACE_PASSWORD", os.environ.get("JUDITH_WORKSPACE_PASSWORD", ""))


def signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(hashlib.sha256(password().encode()).hexdigest(), salt="judith-staff-v1")


def session_data() -> dict | None:
    try:
        return signer().loads(request.cookies.get(COOKIE, ""), max_age=8 * 60 * 60)
    except (BadSignature, SignatureExpired):
        return None


@workspace.before_request
def protect_workspace():
    if not request.path.startswith("/workspace/api/"):
        return None
    if len(password()) < 12:
        return jsonify(error="Staff workspace disabled. Configure JUDITH_WORKSPACE_PASSWORD (at least 12 characters)."), 503
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if request.headers.get("X-Judith-Request") != "workspace":
            return jsonify(error="Missing workspace request header."), 403
        origin = request.headers.get("Origin")
        if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
            return jsonify(error="Cross-origin workspace requests are not allowed."), 403
    if request.endpoint == "workspace.login":
        return None
    session = session_data()
    if not session:
        return jsonify(error="Sign in to the staff workspace."), 401
    g.workspace_session = session
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not secrets.compare_digest(request.headers.get("X-CSRF-Token", "").encode(), session["csrf"].encode()):
            return jsonify(error="Session check failed. Sign in again."), 403


@workspace.after_request
def workspace_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    return response


@workspace.errorhandler(jobs.JobError)
def invalid_job(exc):
    current_app.logger.warning("Workspace request rejected: %s", exc)
    return jsonify(error=str(exc)), exc.status_code


@workspace.errorhandler(BadRequest)
@workspace.errorhandler(UnsupportedMediaType)
def invalid_json(exc):
    return jsonify(error="Send a valid JSON object."), 400


@workspace.errorhandler(RequestEntityTooLarge)
def oversized_upload(exc):
    return jsonify(error="Upload is too large; maximum PDF size is 5 MB."), 413


@workspace.errorhandler(sqlite3.Error)
@workspace.errorhandler(OSError)
def database_error(exc):
    current_app.logger.exception("Workspace database operation failed")
    return jsonify(error="Job storage is unavailable. Your changes were not saved; try again."), 503


def body() -> dict:
    data = request.get_json()
    if not isinstance(data, dict):
        raise jobs.JobError("Send a JSON object.")
    return data


def templates() -> list[dict]:
    path = current_app.config.get("JUDITH_PRICEBOOK", ROOT / "data" / "pricebook.json")
    with open(path, encoding="utf-8") as file:
        return jobs.built_in_templates(json.load(file)) + store().templates()


@workspace.get("")
@workspace.get("/")
def home():
    return render_template("workspace.html")


@workspace.post("/api/login")
def login():
    now = time.time()
    with store().connection(write=True) as db:
        db.execute("CREATE TABLE IF NOT EXISTS workspace_login_attempts "
                   "(address TEXT PRIMARY KEY, started REAL NOT NULL, attempts INTEGER NOT NULL)")
        db.execute("DELETE FROM workspace_login_attempts WHERE started <= ?", (now - 60,))
        address = request.remote_addr or "unknown"
        row = db.execute("SELECT started, attempts FROM workspace_login_attempts WHERE address = ?",
                         (address,)).fetchone()
        if row and row["attempts"] >= 10:
            response = jsonify(error="Too many sign-in attempts. Wait one minute and try again.")
            response.headers["Retry-After"] = str(max(1, int(61 - (now - row["started"]))))
            return response, 429
        db.execute("INSERT INTO workspace_login_attempts VALUES (?, ?, 1) "
                   "ON CONFLICT(address) DO UPDATE SET attempts=attempts+1", (address, now))
    submitted = body().get("password", "")
    if not isinstance(submitted, str) or not secrets.compare_digest(
        hashlib.sha256(submitted.encode()).digest(), hashlib.sha256(password().encode()).digest()
    ):
        return jsonify(error="Incorrect workspace password."), 401
    csrf = secrets.token_hex(32)
    response = jsonify(csrf=csrf)
    response.set_cookie(COOKIE, signer().dumps({"csrf": csrf}), max_age=8 * 60 * 60,
                        httponly=True, samesite="Strict", path="/workspace",
                        secure=current_app.config.get("JUDITH_SECURE_COOKIE", os.environ.get("JUDITH_SECURE_COOKIE") == "1"))
    return response


@workspace.get("/api/session")
def session_info():
    return jsonify(csrf=g.workspace_session["csrf"])


@workspace.post("/api/logout")
def logout():
    response = jsonify(ok=True)
    response.delete_cookie(COOKIE, path="/workspace")
    return response


@workspace.get("/api/templates")
def list_templates():
    return jsonify(templates())


@workspace.get("/api/jobs")
def list_jobs():
    return jsonify([jobs.job_view(job) for job in store().list()])


@workspace.get("/api/export")
def export_jobs():
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Job ID", "Title", "Customer", "Status", "Estimated person-hours", "Estimated direct cost",
                     "Selling price before tax", "Tax", "Customer total", "Actual person-hours",
                     "Actual direct cost", "Direct-cost variance"])
    for saved in store().list():
        job = jobs.job_view(saved)
        totals, actual, comparison = job["totals"], job["actual"], job["comparison"]
        row = [job["id"], job["title"], job["customer"], job["status"], totals["labor_hours"],
               totals["direct_cost"], totals["subtotal"], totals["tax"], totals["total"],
               actual["labor_hours"] if actual else "", comparison["actual_cost"] if comparison else "",
               comparison["direct_cost_variance"] if comparison else ""]
        # Only user-entered text needs spreadsheet formula protection.
        for index in (1, 2):
            if row[index].lstrip().startswith(("=", "+", "-", "@")):
                row[index] = "'" + row[index]
        writer.writerow(row)
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="judith-job-costs.csv"'})


@workspace.post("/api/jobs")
def create_job():
    data = body()
    template_id = data.get("template_id", "")
    if template_id:
        template = next((item for item in templates() if item["id"] == template_id), None)
        if template is None:
            raise jobs.NotFound("Template not found.")
        data = template["job"].copy()
        data["valid_until"] = (date.today() + timedelta(days=30)).isoformat()
    else:
        data = jobs.new_job(data.get("title", "New estimate"))
    return jsonify(jobs.job_view(store().create(data))), 201


@workspace.post("/api/preview")
def preview():
    return jsonify(jobs.calculate(jobs.normalize_job(body())))


@workspace.route("/api/jobs/<job_id>", methods=["GET", "PUT"])
def job_detail(job_id):
    if request.method == "GET":
        job = store().get(job_id)
    else:
        data = body()
        job = store().update(job_id, data, data.get("version"))
    return jsonify(jobs.job_view(job))


@workspace.post("/api/jobs/<job_id>/action")
def job_action(job_id):
    data = body()
    return jsonify(jobs.job_view(store().transition(job_id, data.get("action"), data.get("version"))))


@workspace.post("/api/jobs/<job_id>/revision")
def revise_job(job_id):
    body()
    return jsonify(jobs.job_view(store().revise(job_id))), 201


@workspace.post("/api/jobs/<job_id>/schedule")
def schedule_job(job_id):
    return jsonify(jobs.job_view(store().schedule(job_id, body())))


@workspace.post("/api/jobs/<job_id>/actuals")
def actual_costs(job_id):
    return jsonify(jobs.job_view(store().actuals(job_id, body())))


@workspace.post("/api/jobs/<job_id>/template")
def save_template(job_id):
    return jsonify(store().save_template(job_id, body().get("name", ""))), 201


@workspace.post("/api/price-search")
def search_prices():
    query = jobs.text(body().get("query", ""), "Search query", 200, True)
    try:
        return jsonify(material_prices.search_material_prices(query))
    except material_prices.PriceLookupError as exc:
        current_app.logger.warning("Workspace price search failed: %s", exc)
        return jsonify(error=str(exc)), 503


@workspace.post("/api/import-pdf")
def import_pdf():
    request.max_content_length = 5 * 1024 * 1024
    upload = request.files.get("file")
    if not upload or not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise jobs.JobError("Choose a text-based PDF quantity schedule.")
    from .pdf_import import create_estimate_from_pdf
    path = current_app.config.get("JUDITH_PRICEBOOK", ROOT / "data" / "pricebook.json")
    with open(path, encoding="utf-8") as file:
        pricebook = json.load(file)
    with tempfile.TemporaryDirectory(prefix="judith-pdf-") as directory:
        filename = Path(directory) / "takeoff.pdf"
        upload.save(filename)
        try:
            estimate, matches = create_estimate_from_pdf(str(filename), pricebook)
        except ValueError as exc:
            raise jobs.JobError(str(exc)) from exc
    job = jobs.new_job(Path(upload.filename).stem[:160] or "Imported takeoff")
    job["notes"] = (f"PDF draft: {matches} catalog matches. Verify every quantity, unit, specification and price. "
                    "Labor hours were not inferred. Drawing geometry and OCR are not supported.")
    job["items"] = [{
        "description": row.description, "quantity": str(row.quantity), "unit": row.unit,
        "unit_cost": str(row.unit_price), "hours_per_unit": "0", "waste_percent": "0",
        "supplier": "", "specification": "", "verified_on": "", "customer_supplied": False,
    } for row in estimate.line_items]
    return jsonify(jobs.job_view(store().create(job))), 201


def register_workspace(app: Flask) -> None:
    app.register_blueprint(workspace)


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(config or {})
    register_workspace(app)
    app.add_url_rule("/", "workspace_redirect", lambda: redirect("/workspace"))
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
