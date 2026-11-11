from flask import Flask, request, render_template, jsonify
from estimator import storage, material_prices, labor_rates
import os, smtplib
from email.message import EmailMessage

app = Flask(__name__)

# Customer-facing estimate request form
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        msg = EmailMessage()
        msg["Subject"] = "New estimate request"
        msg["From"] = os.getenv("MAIL_FROM", "noreply@example.com")
        msg["To"] = os.getenv("MAIL_TO", "owner@example.com")
        msg.set_content(f"Name: {data.get('name')}\nEmail: {data.get('email')}\nPhone: {data.get('phone')}\nType: {data.get('project_type')}\nDetails: {data.get('details')}")
        try:
            with smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "587"))) as s:
                s.starttls()
                s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", ""))
                s.send_message(msg)
        except Exception as e:
            return jsonify({"ok": False, "error": "Email failed: " + str(e)}), 500
        return jsonify({"ok": True, "message": "Request submitted! We'll be in touch shortly."})
    return render_template("index.html")

# Pricing API for customers
@app.route("/api/pricing", methods=["POST"])
def api_pricing():
    data = request.get_json(silent=True) or {}
    q = (data.get("query") or "").strip()
    if not q:
        return jsonify({"error": "Query required"}), 400
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

# Labor rate API
@app.route("/api/labor-rate")
def api_labor_rate():
    pb = storage.load_pricebook()
    return jsonify({"rate": storage.get_labor_rate(pb)})

# NEC quick calc
@app.route("/api/nec", methods=["POST"])
def api_nec():
    data = request.get_json(silent=True) or {}
    from estimator.nec import calculate, format_report
    res = calculate(float(data.get("sqft", 1)), float(data.get("amps", 20)))
    return jsonify({"report": format_report(res)})

# Chat endpoint for Harold
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"response": "Please enter a message."})

    from estimator import material_prices
    from estimator.labor_rates import compare_rates
    from estimator.nec import calculate, format_report
    from estimator import storage as storage_mod

    pb = storage.load_pricebook()
    q = message.lower()

    if any(kw in q for kw in ["price", "cost", "material", "wire", "breaker", "box", "receptacle", "switch"]):
        try:
            offers = material_prices.search_material_prices(message)
            storage.set_cached_ai_value(pb, "chat:" + q, offers)
            storage.save_pricebook(pb)
            if offers:
                desc = "; ".join([o.get("description", "unknown") + " - $" + str(o.get("unit_price", 0)) + "/" + o.get("unit", "each") for o in offers[:5]])
                return jsonify({"response": "Found " + str(len(offers)) + " material(s): " + desc})
            return jsonify({"response": "No materials found for that query."})
        except Exception as e:
            return jsonify({"response": "Error: " + str(e)})

    if any(kw in q for kw in ["labor rate", "labor cost", "hourly", "compare labor"]):
        try:
            res = compare_rates(data.get("state", "Maryland"))
            src = ", ".join([s.name + " ($" + str(s.rate) + "/hr)" for s in res.sources])
            return jsonify({"response": "Recommended: $" + str(res.recommended) + "/hr. Sources: " + src})
        except Exception as e:
            return jsonify({"response": "Error: " + str(e)})

    if any(kw in q for kw in ["nec", "calcul", "amp", "voltage", "circuit", "service"]):
        try:
            import re
            sqft = float(re.search(r'(\d+(?:\.\d+)?)', q).group(1)) if re.search(r'(\d+(?:\.\d+)?)', q) else 1
            amps = 20
            res = calculate(sqft, amps)
            return jsonify({"response": format_report(res)})
        except Exception as e:
            return jsonify({"response": "Error: " + str(e)})

    return jsonify({"response": "I'm Harold. I can help with material prices, labor rates, NEC calculations, and estimates. What do you need?"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))