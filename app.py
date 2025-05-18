"""
app.py – Time-Travel QR Codes
Features
1.  Style-able QR (foreground / background colour)
2.  Password-gated reveal
3.  N-times scan limit
4.  Scan logs (SQLite) + simple /logs viewer
"""

from flask import Flask, render_template, request
import qrcode
from io import BytesIO
import base64, sqlite3, os, uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key"

DB_PATH = "scan_logs.db"

# --------------------------------------------------------------------------- #
#  DB helpers                                                                 #
# --------------------------------------------------------------------------- #
def init_db() -> None:
    """Create tables on first run."""
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS scans (
                   id        INTEGER PRIMARY KEY AUTOINCREMENT,
                   ts        TEXT,          -- UTC ISO
                   ip        TEXT,
                   ua        TEXT,
                   weekday   INTEGER,
                   hour      INTEGER,
                   delivered_msg TEXT
               )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS qr_tokens (
                   token     TEXT PRIMARY KEY,
                   password  TEXT,
                   fg_color  TEXT,
                   bg_color  TEXT,
                   max_uses  INTEGER,
                   uses      INTEGER DEFAULT 0
               )"""
        )


def log_scan(ip: str, ua: str, weekday: int, hour: int, delivered_msg: str) -> None:
    """Insert a record into scans table."""
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


# Initialise database once
init_db()

# --------------------------------------------------------------------------- #
#  Routes                                                                      #
# --------------------------------------------------------------------------- #
@app.route("/", methods=["GET", "POST"])
def generate_qr():
    """
    Home page – create a custom QR code.
    POST form fields:
        fg_color   – foreground HEX
        bg_color   – background HEX
        password   – optional
        max_uses   – integer ≥1
    """
    if request.method == "POST":
<<<<<<< HEAD
        fg = request.form.get("fg_color", "#000000")
        bg = request.form.get("bg_color", "#ffffff")
        password = request.form.get("password", "").strip()
        try:
            max_uses = max(1, int(request.form.get("max_uses", 1)))
        except ValueError:
            max_uses = 1

        # Generate a short token
        token = uuid.uuid4().hex[:10]
=======
        data = request.form['text']
        qr = qrcode.make(data)
        # Save the QR code to a BytesIO object
        img_io = BytesIO()
        qr.save(img_io, 'PNG')
        img_io.seek(0)
>>>>>>> a6898185a1a84bb6f689a51b829f678a44df4489

        # Save token metadata
        with sqlite3.connect(DB_PATH) as con:
            con.execute(
                "INSERT INTO qr_tokens (token, password, fg_color, bg_color, max_uses) "
                "VALUES (?, ?, ?, ?, ?)",
                (token, password, fg, bg, max_uses),
            )

        # Create styled QR that points to /reveal/<token>
        qr_url = request.url_root.rstrip("/") + "/reveal/" + token
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color=fg, back_color=bg)

        # Encode PNG to base64 for inline display
        buf = BytesIO(); img.save(buf, "PNG"); buf.seek(0)
        qr_b64 = base64.b64encode(buf.read()).decode()

        return render_template(
            "index.html",
            qr_code=qr_b64,
            qr_link=qr_url,
        )

    return render_template("index.html", qr_code=None)


@app.route("/reveal/<token>", methods=["GET", "POST"])
def reveal_token(token: str):
    """Step-wise reveal: (1) password prompt (if set)  (2) deliver message."""
    # Fetch token record
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM qr_tokens WHERE token=?", (token,)).fetchone()

    if not row:
        return "❌ Invalid QR token.", 404

    # If token exhausted
    if row["uses"] >= row["max_uses"]:
        return "❌ QR code usage limit exceeded.", 403

    # If password is required
    if row["password"]:
        if request.method == "GET":
            # Show password entry page
            return render_template("password_prompt.html", token=token)

        # POST – check password
        input_pwd = request.form.get("password", "")
        if input_pwd != row["password"]:
            return "❌ Wrong password.", 401

    # --- deliver dynamic time-based message ---
    now = datetime.now()
    hour, weekday = now.hour, now.weekday()

    if weekday >= 5:
        message = "🎉 It's the weekend! Time to relax and recharge."
    elif 6 <= hour < 12:
        message = "🌞 Good morning! Start your day with a smile."
    elif 12 <= hour < 18:
        message = "☀️ Good afternoon! Stay productive and focused."
    elif 18 <= hour < 22:
        message = "🌆 Good evening! Take a break and enjoy some leisure."
    else:
        message = "🌙 It's late night! Time to rest. Sweet dreams."

    if now.strftime("%m-%d") == "01-01":
        message += " 🎊 Happy New Year!"

    # Increment usage counter
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE qr_tokens SET uses = uses + 1 WHERE token=?", (token,))

    # Log this scan
    log_scan(
        request.remote_addr or "unknown",
        request.headers.get("User-Agent", "unknown"),
        weekday,
        hour,
        message,
    )

    return render_template("reveal.html", message=message)


@app.route("/logs")
def logs():
    """Very simple read-only scan viewer (last 200)."""
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM scans ORDER BY id DESC LIMIT 200"
        ).fetchall()
    return render_template("logs.html", rows=rows)


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    app.run(debug=True)
