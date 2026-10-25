from flask import Flask, request, render_template_string
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
    return render_template_string(HTML)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
