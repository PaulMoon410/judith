"""API documentation for Judith Electrical Estimator."""

from flask import jsonify, render_template_string

OPENAPI_HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Judith API Documentation</title>
<style>
body{font-family:system-ui,Arial;margin:0;background:#0b1220;color:#e6ecf7}
.container{max-width:1000px;margin:0 auto;padding:32px 20px}
h1{color:#fbbf24;font-size:28px}
h2{color:#3b82f6;font-size:20px;margin-top:32px;border-bottom:1px solid #26334f;padding-bottom:8px}
.endpoint{background:#131c2e;border:1px solid #26334f;border-radius:12px;padding:20px;margin:16px 0}
.method{display:inline-block;padding:4px 10px;border-radius:6px;font-weight:700;font-size:12px}
.get{background:#10b981;color:#052e1f}
.post{background:#3b82f6;color:#052e1f}
.path{font-family:monospace;font-size:16px;color:#fbbf24;margin-left:8px}
.desc{color:#8fa0bf;font-size:14px;margin:8px 0 12px}
code{background:#0d1526;padding:2px 6px;border-radius:4px;font-size:13px}
pre{background:#0d1526;padding:14px;border-radius:8px;overflow:auto;font-size:13px}
pre code{background:none;padding:0}
</style>
</head>
<body>
<div class="container">
<h1>Judith Electrical Estimator API</h1>
<p>RESTful API for customer-facing electrical estimation services.</p>

<h2>Endpoints</h2>

<div class="endpoint">
<span class="method get">GET</span><span class="path">/health</span>
<div class="desc">Health check endpoint. Returns service status and timestamp.</div>
<pre><code>Response: {"status": "ok", "service": "judith-estimator", "timestamp": "..."}</code></pre>
</div>

<div class="endpoint">
<span class="method get">GET</span><span class="path">/</span>
<div class="desc">Main application page. Serves the customer-facing estimate request form.</div>
</div>

<div class="endpoint">
<span class="method post">POST</span><span class="path">/</span>
<div class="desc">Submit an estimate request. Sends email notification to business owner.</div>
<pre><code>Body: {
  "name": "string (required)",
  "email": "string (required, valid email)",
  "phone": "string (optional)",
  "project_type": "string (optional)",
  "details": "string (required)"
}

Response: {"ok": true, "message": "Request submitted!"} or {"ok": false, "error": "..."}
</code></pre>
</div>

<div class="endpoint">
<span class="method post">POST</span><span class="path">/api/pricing</span>
<div class="desc">Search live material prices via SerpApi. Results cached in FTP-backed pricebook.</div>
<pre><code>Body: {"query": "string (required, max 200 chars)"}

Response: Array of {description, price, unit, source}
</code></pre>
</div>

<div class="endpoint">
<span class="method get">GET</span><span class="path">/api/labor-rate</span>
<div class="desc">Get recommended electrician labor rate for Maryland (default state).</div>
<pre><code>Response: {"rate": 85.0}
</code></pre>
</div>

<div class="endpoint">
<span class="method post">POST</span><span class="path">/api/nec</span>
<div class="desc">NEC 220 dwelling unit load calculation.</div>
<pre><code>Body: {"sqft": number (positive), "amps": number (positive, default 20)}

Response: {"report": "formatted NEC calculation report"}
</code></pre>
</div>

<div class="endpoint">
<span class="method post">POST</span><span class="path">/api/chat</span>
<div class="desc">AI-powered Harold assistant for material prices, labor rates, NEC questions.</div>
<pre><code>Body: {"message": "string (required, max 500 chars)"}

Response: {"response": "string"}
</code></pre>
</div>

<h2>Rate Limiting</h2>
<p>All endpoints are rate-limited to prevent abuse:</p>
<ul>
<li><code>/api/pricing</code>: 30 requests/minute</li>
<li><code>/api/chat</code>: 20 requests/minute</li>
<li><code>/api/nec</code>: 30 requests/minute</li>
<li><code>/</code>: 10 requests/hour</li>
</ul>

<h2>Authentication</h2>
<p>API endpoints are public. CSRF protection is enabled for form submissions.</p>

<h2>Errors</h2>
<p>Standard HTTP error codes are used:</p>
<ul>
<li><code>400</code>: Bad Request (missing/invalid input)</li>
<li><code>404</code>: Not Found</li>
<li><code>429</code>: Too Many Requests (rate limit exceeded)</li>
<li><code>500</code>: Internal Server Error</li>
<li><code>503</code>: Service Unavailable (external API down)</li>
</ul>

<h2>Examples</h2>
<pre><code># Health check
curl http://localhost:5000/health

# Price search
curl -X POST http://localhost:5000/api/pricing \
  -H "Content-Type: application/json" \
  -d '{"query": "12/2 Romex 250ft"}'

# NEC calculation
curl -X POST http://localhost:5000/api/nec \
  -H "Content-Type: application/json" \
  -d '{"sqft": 1500, "amps": 20}'
</code></pre>

</div>
</body>
</html>
"""

def api_docs():
    """Serve OpenAPI-style API documentation."""
    from flask import current_app
    return render_template_string(OPENAPI_HTML)


def api_openapi_spec():
    """Serve OpenAPI 3.0 JSON specification."""
    from flask import current_app
    return jsonify({
        "openapi": "3.0.0",
        "info": {
            "title": "Judith Electrical Estimator API",
            "version": "1.0.0",
            "description": "RESTful API for customer-facing electrical estimation services"
        },
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "responses": {"200": {"description": "Service is healthy"}}
                }
            },
            "/api/pricing": {
                "post": {
                    "summary": "Search material prices",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "maxLength": 200}
                                    },
                                    "required": ["query"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Price search results"},
                        "400": {"description": "Invalid request"},
                        "503": {"description": "Service unavailable"}
                    }
                }
            },
            "/api/labor-rate": {
                "get": {
                    "summary": "Get labor rate",
                    "responses": {"200": {"description": "Labor rate"}}
                }
            },
            "/api/nec": {
                "post": {
                    "summary": "NEC calculation",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "sqft": {"type": "number", "minimum": 0},
                                        "amps": {"type": "number", "minimum": 0, "default": 20}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "NEC report"}}
                }
            },
            "/api/chat": {
                "post": {
                    "summary": "Chat with Harold",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "message": {"type": "string", "maxLength": 500}
                                    },
                                    "required": ["message"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Chat response"}}
                }
            }
        }
    })


def register_api_docs(app):
    """Register API documentation routes on the Flask app."""
    app.add_url_rule("/api/docs", "api_docs", api_docs, methods=["GET"])
    app.add_url_rule("/api/openapi.json", "api_openapi", api_openapi_spec, methods=["GET"])