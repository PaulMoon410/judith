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
        msg.set_content("Name: " + request.form.get('name') + "\nEmail: " + request.form.get('email') + "\n" + request.form.get('desc'))
        try:
            with smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "587"))) as s:
                s.starttls()
                s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", ""))
                s.send_message(msg)
        except Exception as e:
            return "Email failed: " + str(e)
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
    est = Estimate(title=data.get("title", "Untitled"), state=data.get("state", "Maryland"))
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

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Handle chat messages from the frontend Harold assistant.

    Accepts a JSON payload with a 'message' field and returns a JSON response
    with either a 'response' or 'answer' key. Routes electrical estimation
    questions to the appropriate estimator modules.
    """
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"response": "Please enter a message."})

    from estimator import material_prices
    from estimator.labor_rates import compare_rates
    from estimator.nec import calculate, format_report
    from estimator import storage as storage_mod

    pb = material_prices.load_pricebook() if hasattr(material_prices, 'load_pricebook') else storage.load_pricebook()
    q = message.lower()

    # Route to material price search
    if any(kw in q for kw in ["price", "cost", "material", "wire", "breaker", "box", "receptacle", "switch"]):
        try:
            offers = material_prices.search_material_prices(message)
            storage.set_cached_ai_value(pb, "chat:" + q, offers)
            storage.save_pricebook(pb)
            if offers:
                desc_parts = []
                for o in offers[:5]:
                    d = o.get("description", "unknown")
                    p = o.get("unit_price", 0)
                    u = o.get("unit", "each")
                    desc_parts.append(d + " - $" + str(p) + "/" + u)
                return jsonify({"response": "Found " + str(len(offers)) + " material(s): " + "; ".join(desc_parts)})
            return jsonify({"response": "I couldn't find any materials matching that query."})
        except Exception as e:
            return jsonify({"response": "Error searching materials: " + str(e)})

    # Route to labor rate comparison
    if any(kw in q for kw in ["labor rate", "labor cost", "hourly", "compare labor"]):
        try:
            res = compare_rates(data.get("state", "Maryland"))
            sources = [s.__dict__ for s in res.sources]
            src_parts = []
            for s in sources:
                n = s.get("name", "")
                r = s.get("rate", "")
                src_parts.append(n + " ($" + str(r) + "/hr)")
            return jsonify({"response": "Recommended labor rate: $" + str(res.recommended) + "/hr. Sources: " + ", ".join(src_parts)})
        except Exception as e:
            return jsonify({"response": "Error comparing labor rates: " + str(e)})

    # Route to NEC calculations
    if any(kw in q for kw in ["nec", "calcul", "amp", "voltage", "circuit", "service"]):
        try:
            import re
            sqft_match = re.search(r'(\d+(?:\.\d+)?)\s*sq\.?\s*ft|area[=:]\s*(\d+(?:\.\d+)?)', q)
            amps_match = re.search(r'(\d+)\s*amp|service[=:]\s*(\d+)(?:A| amps?)', q)
            sqft = 1
            if sqft_match:
                if sqft_match.group(1):
                    sqft = float(sqft_match.group(1))
                elif sqft_match.group(2):
                    sqft = float(sqft_match.group(2))
            amps = 20
            if amps_match:
                if amps_match.group(1):
                    amps = float(amps_match.group(1))
                elif amps_match.group(2):
                    amps = float(amps_match.group(2))
            res = calculate(sqft, amps)
            return jsonify({"response": format_report(res)})
        except Exception as e:
            return jsonify({"response": "Error with NEC calculation: " + str(e)})

    # Route to materials list
    if any(kw in q for kw in ["materials", "what do you offer", "catalog", "inventory"]):
        try:
            materials = storage_mod.get_materials(pb)
            if materials:
                m_desc = "; ".join([m.description + " ($" + str(m.unit_price) + "/" + m.unit + ")" for m in materials[:8]])
                return jsonify({"response": "We carry: " + m_desc + ("..." if len(materials) > 8 else "")})
            return jsonify({"response": "No materials found in the pricebook."})
        except Exception as e:
            return jsonify({"response": "Error loading materials: " + str(e)})

    # Default response for unrecognized questions
    return jsonify({"response": "I'm Harold, your electrical estimation assistant. I can help you with material prices, labor rates, NEC calculations, and creating estimates. What would you like to know?"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))