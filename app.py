from flask import Flask, request, render_template, jsonify
from estimator import storage, material_prices, labor_rates
import os, smtplib
from email.message import EmailMessage

app = Flask(__name__)

HTML = """<h1>Estimate Request</h1>
<form method=post>
Name: <input name=name><br>
Email: <input name=email><br>
Description: <textarea name=desc></textarea><br>
<button>Submit</button>
</form>"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        msg = EmailMessage()
        msg["Subject"] = "New estimate request"
        msg["From"] = os.getenv("MAIL_FROM", "noreply@example.com")
        msg["To"] = os.getenv("MAIL_TO", "owner@example.com")
        msg.set_content(f"Name: {request.form.get('name')}\nEmail: {request.form.get('email')}\n{request.form.get('desc')}")
        try:
            with smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "587"))) as s:
                s.starttls()
                s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", ""))
                s.send_message(msg)
        except Exception as e:
            return f"Email failed: {e}"
        # QuickBooks placeholder: push to QBO API here with OAuth token
        return "Submitted! We'll be in touch."
    return render_template("index.html")

@app.route("/api/materials")
def api_materials():
    pb = storage.load_pricebook()
    return jsonify([m.__dict__ for m in storage.get_materials(pb)])


@app.route("/api/labor-rate")
def api_labor_rate():
    pb = storage.load_pricebook()
    return jsonify({"rate": storage.get_labor_rate(pb)})


@app.route("/api/price-search", methods=["POST"])
def api_price_search():
    data = request.get_json(silent=True) or {}
    q = (data.get("query") or "").strip()
    pb = storage.load_pricebook()
    key = "price_search:" + q.lower()
    cached = storage.get_cached_ai_value(pb, key)
    if cached is not None:
        return jsonify(cached)
    try:
        offers = material_prices.search_material_prices(q)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    storage.set_cached_ai_value(pb, key, offers)
    storage.save_pricebook(pb)
    return jsonify(offers)


@app.route("/api/estimates")
def api_estimates_list():
    return jsonify(storage.list_saved_estimates())


@app.route("/api/estimate", methods=["POST"])
def api_estimate_create():
    data = request.get_json(silent=True) or {}
    from estimator.models import Estimate, LineItem
    est = Estimate(title=data.get("title","Untitled"), state=data.get("state","Maryland"))
    storage.save_estimate(est)
    return jsonify({"saved": True, "title": est.title})


@app.route("/api/nec", methods=["POST"])
def api_nec():
    data = request.get_json(silent=True) or {}
    from estimator.nec import calculate, format_report
    res = calculate(float(data.get("sqft", 1)), float(data.get("amps", 20)))
    return jsonify({"report": format_report(res)})


@app.route("/api/labor-compare", methods=["POST"])
def api_labor_compare():
    data = request.get_json(silent=True) or {}
    from estimator.labor_rates import compare_rates
    res = compare_rates(data.get("state", "Maryland"))
    return jsonify({"recommended": res.recommended, "sources": [s.__dict__ for s in res.sources]})


@app.route("/api/pricebook", methods=["GET", "PUT"])
def api_pricebook():
    if request.method == "GET":
        return jsonify(storage.load_pricebook())
    storage.save_pricebook(request.get_json(silent=True) or {})
    return jsonify({"saved": True})


@app.route("/api/estimates/<name>")
def api_estimate_load(name):
    try:
        est = storage.load_estimate(name)
        return jsonify(est.to_dict())
    except FileNotFoundError:
        return jsonify({"error": "not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
