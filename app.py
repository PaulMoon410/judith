from flask import Flask, request, render_template, jsonify, g
from estimator import storage, material_prices, labor_rates
import os, smtplib, logging, sys, uuid, time, functools
from email.message import EmailMessage
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

# Circuit breaker state
_circuit_breakers = {}

def circuit_breaker(key, failure_threshold=5, recovery_timeout=60):
    """Simple circuit breaker decorator."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cb = _circuit_breakers.setdefault(key, {"failures": 0, "last_failure": 0, "open": False})
            now = time.time()
            if cb["open"] and now - cb["last_failure"] > recovery_timeout:
                cb["open"] = False
                cb["failures"] = 0
                logger.info("circuit_breaker_reset", key=key)
            if cb["open"]:
                logger.warning("circuit_breaker_open", key=key)
                raise Exception(f"Circuit breaker open for {key}")
            try:
                result = func(*args, **kwargs)
                if cb["failures"] > 0:
                    cb["failures"] = 0
                return result
            except Exception as e:
                cb["failures"] += 1
                cb["last_failure"] = now
                if cb["failures"] >= failure_threshold:
                    cb["open"] = True
                    logger.error("circuit_breaker_opened", key=key, failures=cb["failures"])
                raise
        return wrapper
    return decorator

# Retry decorator with exponential backoff
def with_retry(key, max_attempts=3, min_wait=1, max_wait=10):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logger.error("retry_exhausted", key=key, attempts=attempt + 1, error=str(e))
                        raise
                    wait_time = min(min_wait * (2 ** attempt), max_wait)
                    logger.warning("retry_attempt", key=key, attempt=attempt + 1, wait=wait_time, error=str(e))
                    time.sleep(wait_time)
        return wrapper
    return decorator

# Environment validation
REQUIRED_ENV = ["MAIL_TO", "SMTP_USER", "SMTP_PASS"]
OPTIONAL_ENV = {
    "MAIL_FROM": "noreply@example.com",
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": "587",
    "SERPAPI_KEY": "",
    "FTP_HOST": "",
    "FTP_USER": "",
    "FTP_PASS": "",
    "FTP_PRICEBOOK_PATH": "/ai/brain/pricebook.json",
    "PORT": "5000",
}

def validate_env():
    missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
    if missing:
        logger.error("missing_required_env", vars=missing)
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    for k, default in OPTIONAL_ENV.items():
        if not os.getenv(k) and default:
            os.environ[k] = default
    logger.info("environment_validated", required=REQUIRED_ENV, optional=list(OPTIONAL_ENV.keys()))

app = Flask(__name__)
from estimator.workspace_web import register_workspace
register_workspace(app)
app.config["WTF_CSRF_ENABLED"] = True
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(32).hex())

# Secure headers
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    # HSTS only in production
    if os.getenv("FLASK_ENV") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Request ID + structured logging
@app.before_request
def before_request():
    g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    g.start_time = time.time()
    structlog.contextvars.bind_contextvars(request_id=g.request_id, path=request.path, method=request.method)

@app.after_request
def after_request(response):
    duration = time.time() - g.start_time
    logger.info("http_request",
        request_id=g.request_id,
        path=request.path,
        method=request.method,
        status=response.status_code,
        duration_ms=round(duration * 1000, 2)
    )
    response.headers["X-Request-ID"] = g.request_id
    return response

# Health check
@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "judith-estimator", "timestamp": datetime.utcnow().isoformat()})

# Rate limiting
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
    )
except ImportError:
    logger.warning("flask_limiter_not_available")
    limiter = None

# Customer-facing estimate request form
@app.route("/", methods=["GET", "POST"])
@limiter.limit("10 per hour") if limiter else lambda f: f
def index():
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        # Basic validation
        required = ["name", "email", "details"]
        for field in required:
            if not data.get(field):
                return jsonify({"ok": False, "error": f"Missing required field: {field}"}), 400
        # Basic email format check
        email = data.get("email", "")
        if "@" not in email or "." not in email.split("@")[-1]:
            return jsonify({"ok": False, "error": "Invalid email format"}), 400

        msg = EmailMessage()
        msg["Subject"] = "New estimate request"
        msg["From"] = os.getenv("MAIL_FROM", "noreply@example.com")
        msg["To"] = os.getenv("MAIL_TO", "owner@example.com")
        msg.set_content(f"Name: {data.get('name')}\nEmail: {data.get('email')}\nPhone: {data.get('phone')}\nType: {data.get('project_type')}\nDetails: {data.get('details')}")

        try:
            with smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "587")), timeout=10) as s:
                s.starttls()
                s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", ""))
                s.send_message(msg)
        except Exception as e:
            logger.error("email_failed", error=str(e), request_id=g.request_id)
            return jsonify({"ok": False, "error": "Email delivery failed. Please try again or call us."}), 500

        logger.info("estimate_submitted", name=data.get("name"), email=data.get("email"), request_id=g.request_id)
        return jsonify({"ok": True, "message": "Request submitted! We'll be in touch shortly."})

    return render_template("index.html")

# Pricing API for customers
@app.route("/api/pricing", methods=["POST"])
@limiter.limit("30 per minute") if limiter else lambda f: f
def api_pricing():
    data = request.get_json(silent=True) or {}
    q = (data.get("query") or "").strip()
    if not q:
        return jsonify({"error": "Query required"}), 400
    if len(q) > 200:
        return jsonify({"error": "Query too long"}), 400

    pb = _get_cached_pricebook()
    key = "price_search:" + q.lower()
    cached = storage.get_cached_ai_value(pb, key)
    if cached is not None:
        logger.debug("price_search_cache_hit", query=q, request_id=g.request_id)
        return jsonify(cached)

    @with_retry("serpapi", max_attempts=3)
    @circuit_breaker("serpapi")
    def search_with_retry(query):
        return material_prices.search_material_prices(query)

    try:
        offers = search_with_retry(q)
    except Exception as e:
        logger.error("price_search_failed", query=q, error=str(e), request_id=g.request_id)
        # Graceful degradation: return cached results if available
        all_cached = {k: v for k, v in pb.get("ai_cache", {}).items() if k.startswith("price_search:")}
        if all_cached:
            logger.info("price_search_degraded", query=q, cached_results=len(all_cached))
            return jsonify({"results": [], "degraded": True, "message": "Live search unavailable, showing cached results"})
        return jsonify({"error": "Price search temporarily unavailable"}), 503

    storage.set_cached_ai_value(pb, key, offers)
    _save_pricebook_with_retry(pb)
    logger.info("price_search_success", query=q, results=len(offers), request_id=g.request_id)
    return jsonify(offers)

# In-memory pricebook cache
_pricebook_cache = {"data": None, "timestamp": 0}
_PRICEBOOK_TTL = 300  # 5 minutes

def _get_cached_pricebook():
    now = time.time()
    if _pricebook_cache["data"] is None or now - _pricebook_cache["timestamp"] > _PRICEBOOK_TTL:
        try:
            _pricebook_cache["data"] = storage.load_pricebook()
            _pricebook_cache["timestamp"] = now
        except Exception as e:
            logger.error("pricebook_load_failed", error=str(e))
            if _pricebook_cache["data"] is None:
                raise
    return _pricebook_cache["data"]

@with_retry("ftp_save", max_attempts=3)
def _save_pricebook_with_retry(pricebook):
    storage.save_pricebook(pricebook)

# Labor rate API
@app.route("/api/labor-rate")
@limiter.limit("60 per minute") if limiter else lambda f: f
def api_labor_rate():
    pb = _get_cached_pricebook()
    return jsonify({"rate": storage.get_labor_rate(pb)})

# NEC quick calc
@app.route("/api/nec", methods=["POST"])
@limiter.limit("30 per minute") if limiter else lambda f: f
def api_nec():
    data = request.get_json(silent=True) or {}
    try:
        sqft = float(data.get("sqft", 1))
        amps = float(data.get("amps", 20))
        if sqft <= 0 or amps <= 0:
            return jsonify({"error": "sqft and amps must be positive"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid sqft or amps"}), 400

    from estimator.nec import calculate, format_report
    res = calculate(sqft, amps)
    return jsonify({"report": format_report(res)})

# Chat endpoint for Harold
@app.route("/api/chat", methods=["POST"])
@limiter.limit("20 per minute") if limiter else lambda f: f
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"response": "Please enter a message."})
    if len(message) > 500:
        return jsonify({"response": "Message too long"}), 400

    from estimator import material_prices
    from estimator.labor_rates import compare_rates
    from estimator.nec import calculate, format_report
    from estimator import storage as storage_mod

    pb = _get_cached_pricebook()
    q = message.lower()

    # Material price search
    if any(kw in q for kw in ["price", "cost", "material", "wire", "breaker", "box", "receptacle", "switch"]):
        try:
            offers = material_prices.search_material_prices(message)
            storage.set_cached_ai_value(pb, "chat:" + q, offers)
            _save_pricebook_with_retry(pb)
            if offers:
                desc = "; ".join([o.get("description", "unknown") + " - $" + str(o.get("unit_price", 0)) + "/" + o.get("unit", "each") for o in offers[:5]])
                return jsonify({"response": "Found " + str(len(offers)) + " material(s): " + desc})
            return jsonify({"response": "No materials found for that query."})
        except Exception as e:
            logger.error("chat_material_search_failed", error=str(e), request_id=g.request_id)
            return jsonify({"response": "Error searching materials. Please try again."})

    # Labor rate comparison
    if any(kw in q for kw in ["labor rate", "labor cost", "hourly", "compare labor"]):
        try:
            res = compare_rates(data.get("state", "Maryland"))
            src = ", ".join([s.name + " ($" + str(s.rate) + "/hr)" for s in res.sources])
            return jsonify({"response": "Recommended: $" + str(res.recommended) + "/hr. Sources: " + src})
        except Exception as e:
            logger.error("chat_labor_failed", error=str(e), request_id=g.request_id)
            return jsonify({"response": "Error getting labor rates."})

    # NEC calculations
    if any(kw in q for kw in ["nec", "calcul", "amp", "voltage", "circuit", "service"]):
        try:
            import re
            sqft_match = re.search(r'(\d+(?:\.\d+)?)', q)
            sqft = float(sqft_match.group(1)) if sqft_match else 1
            amps = 20
            res = calculate(sqft, amps)
            return jsonify({"response": format_report(res)})
        except Exception as e:
            logger.error("chat_nec_failed", error=str(e), request_id=g.request_id)
            return jsonify({"response": "Error with NEC calculation."})

    return jsonify({"response": "I'm Harold. I can help with material prices, labor rates, NEC calculations, and estimates. What do you need?"})

from docs.api_docs import api_docs as _api_docs, api_openapi_spec as _api_openapi_spec

@app.route("/api/docs", methods=["GET"])
def api_docs_view():
    return _api_docs()

@app.route("/api/openapi.json", methods=["GET"])
def api_openapi():
    return _api_openapi_spec()