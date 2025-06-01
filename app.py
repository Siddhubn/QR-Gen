from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import qrcode
from io import BytesIO
import base64
import sqlite3
import uuid
from datetime import datetime
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "super_secret_key"

DB_PATH = "scan_logs.db"

# Google reCAPTCHA keys (set your own keys or env vars)
RECAPTCHA_SITE_KEY = os.environ.get("RECAPTCHA_SITE_KEY") or "YOUR_RECAPTCHA_SITE_KEY"
RECAPTCHA_SECRET_KEY = os.environ.get("RECAPTCHA_SECRET_KEY") or "YOUR_RECAPTCHA_SECRET_KEY"

# Rate limiter: max 10 QR codes generated per IP per hour
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["10 per hour"]
)
limiter.init_app(app)

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS scans (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   ts TEXT,
                   ip TEXT,
                   ua TEXT,
                   weekday INTEGER,
                   hour INTEGER,
                   delivered_msg TEXT
               )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS qr_tokens (
                   token TEXT PRIMARY KEY,
                   password TEXT,
                   fg_color TEXT,
                   bg_color TEXT,
                   max_uses INTEGER,
                   uses INTEGER DEFAULT 0
               )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                   token TEXT PRIMARY KEY,
                   message TEXT,
                   password TEXT,
                   max_uses INTEGER,
                   scans INTEGER DEFAULT 0
               )"""
        )

def log_scan(ip: str, ua: str, weekday: int, hour: int, delivered_msg: str) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """INSERT INTO scans (ts, ip, ua, weekday, hour, delivered_msg)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                datetime.utcnow().isoformat(sep=" ", timespec="seconds"),
                ip,
                ua[:150],
                weekday,
                hour,
                delivered_msg[:200],
            ),
        )

init_db()

def verify_recaptcha(response_token: str) -> bool:
    """Verify Google reCAPTCHA v2 response (currently NOT used in dev)"""
    url = "https://www.google.com/recaptcha/api/siteverify"
    data = {
        "secret": RECAPTCHA_SECRET_KEY,
        "response": response_token,
        "remoteip": request.remote_addr,
    }
    r = requests.post(url, data=data)
    result = r.json()
    return result.get("success", False)

@app.route("/", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def index():
    qr_code = None
    qr_link = None
    download_token = None

    if request.method == "POST":
        # CAPTCHA verification - comment out for dev to disable captcha
        # captcha_response = request.form.get("g-recaptcha-response", "")
        # if not verify_recaptcha(captcha_response):
        #     flash("❌ CAPTCHA verification failed. Please try again.", "danger")
        #     return redirect(url_for("index"))

        fg_color = request.form.get("fg_color", "#000000")
        bg_color = request.form.get("bg_color", "#ffffff")
        password = request.form.get("password", "").strip()
        max_uses_raw = request.form.get("max_uses", "1")
        try:
            max_uses = max(1, int(max_uses_raw))
        except ValueError:
            max_uses = 1

        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()

        if email:
            qr_data = f"mailto:{email}"
        elif message:
            qr_data = message
        else:
            flash("❌ Please provide an email or a message to encode.", "danger")
            return redirect(url_for("index"))

        token = uuid.uuid4().hex[:10]

        with sqlite3.connect(DB_PATH) as con:
            con.execute(
                "INSERT INTO qr_tokens (token, password, fg_color, bg_color, max_uses) "
                "VALUES (?, ?, ?, ?, ?)",
                (token, password, fg_color, bg_color, max_uses),
            )
            con.execute(
                "INSERT OR REPLACE INTO messages (token, message, password, max_uses, scans) "
                "VALUES (?, ?, ?, ?, 0)",
                (token, qr_data, password, max_uses),
            )

        qr_url = request.url_root.rstrip("/") + "/reveal/" + token
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color=fg_color, back_color=bg_color)

        buffered = BytesIO()
        img.save(buffered, format="PNG")
        buffered.seek(0)
        img_b64 = base64.b64encode(buffered.getvalue()).decode()

        session["qr_image"] = buffered.getvalue()
        session["download_token"] = token

        qr_code = img_b64
        qr_link = qr_url
        download_token = token

    return render_template(
        "index.html",
        qr_code=qr_code,
        qr_link=qr_link,
        download_token=download_token,
        recaptcha_site_key=RECAPTCHA_SITE_KEY,
    )

@app.route("/download/<token>")
def download_qr(token):
    if "download_token" not in session or session["download_token"] != token:
        return "❌ Unauthorized or expired download link.", 403

    img_data = session.get("qr_image")
    if not img_data:
        return "❌ No QR code available for download.", 404

    return send_file(
        BytesIO(img_data),
        mimetype="image/png",
        download_name=f"qr_{token}.png",
        as_attachment=True,
    )

@app.route("/reveal/<token>", methods=["GET", "POST"])
def reveal_token(token: str):
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM qr_tokens WHERE token=?", (token,)).fetchone()
        msg_row = con.execute("SELECT * FROM messages WHERE token=?", (token,)).fetchone()

    if not row or not msg_row:
        return "❌ Invalid QR token.", 404

    if row["uses"] >= row["max_uses"]:
        return "❌ QR code usage limit exceeded.", 403

    if row["password"]:
        if request.method == "GET":
            return render_template("password_prompt.html", token=token)

        input_pwd = request.form.get("password", "")
        if input_pwd != row["password"]:
            return "❌ Wrong password.", 401

    now = datetime.now()
    hour, weekday = now.hour, now.weekday()

    if weekday >= 5:
        time_message = "🎉 It's the weekend! Time to relax and recharge."
    elif 6 <= hour < 12:
        time_message = "🌞 Good morning! Start your day with a smile."
    elif 12 <= hour < 18:
        time_message = "☀️ Good afternoon! Stay productive and focused."
    elif 18 <= hour < 22:
        time_message = "🌆 Good evening! Take a break and enjoy some leisure."
    else:
        time_message = "🌙 It's late night! Time to rest. Sweet dreams."

    if now.strftime("%m-%d") == "01-01":
        time_message += " 🎊 Happy New Year!"

    final_message = f"{msg_row['message']} \n\n{time_message}"

    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE qr_tokens SET uses = uses + 1 WHERE token=?", (token,))
        con.execute("UPDATE messages SET scans = scans + 1 WHERE token=?", (token,))

    log_scan(
        request.remote_addr or "unknown",
        request.headers.get("User-Agent", "unknown"),
        weekday,
        hour,
        final_message,
    )

    return render_template("reveal.html", message=final_message)

@app.route("/logs")
def logs():
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM scans ORDER BY id DESC LIMIT 200"
        ).fetchall()
    return render_template("logs.html", rows=rows)

if __name__ == "__main__":
    app.run(debug=True)
