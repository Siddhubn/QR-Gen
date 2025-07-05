from flask import Flask, render_template, request, send_file
import qrcode
from io import BytesIO
import base64
from PIL import Image
import os
import re
import requests
from pyzbar.pyzbar import decode

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

NATURE_LABELS = [
    ("Sky", "#87ceeb"),
    ("Lava", "#cf1020"),
    ("Forest", "#228b22"),
    ("Ocean", "#1e90ff"),
    ("Magma", "#ff4500"),
    ("Sand", "#f4e285"),
    ("Leaf", "#7cfc00"),
    ("Cloud", "#f0f8ff"),
    ("Stone", "#a9a9a9"),
    ("Sun", "#ffd700")
]

def embed_logo(qr_img, logo_file):
    logo = Image.open(logo_file)
    qr_img = qr_img.convert("RGBA")
    logo = logo.convert("RGBA")
    # Resize logo
    qr_w, qr_h = qr_img.size
    factor = 4
    size = qr_w // factor
    logo.thumbnail((size, size), Image.LANCZOS)
    # Center logo
    pos = ((qr_w - logo.width) // 2, (qr_h - logo.height) // 2)
    qr_img.paste(logo, pos, mask=logo)
    return qr_img

@app.route("/", methods=["GET", "POST"])
def generate_qr():
    if request.method == "POST":
        if request.form.get('multi_mode') == '1':
            texts = request.form.getlist('multi_text')[:10]
            multi_qr_results = []
            for idx, text in enumerate(texts):
                if text.strip():
                    label, color = NATURE_LABELS[idx]
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_H,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(text)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color=color, back_color="white")
                    img_io = BytesIO()
                    img.save(img_io, 'PNG')
                    img_io.seek(0)
                    qr_img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
                    # Trust check for each QR
                    trust_result = None
                    is_url = re.match(r'^https?://', text.strip())
                    if is_url:
                        trust_result = check_url_trust(text.strip())
                    else:
                        trust_result = {'score': 'safe', 'icon': '✅', 'reason': 'No issues detected', 'url': text.strip()}
                    multi_qr_results.append({
                        'label': label,
                        'color': color,
                        'text': text,
                        'qr_img': qr_img_base64,
                        'trust_result': trust_result
                    })
            return render_template('index.html', multi_qr_results=multi_qr_results, nature_labels=NATURE_LABELS)
        else:
            data = request.form['text']
            qr_color = request.form.get('qr_color', '#000000')
            bg_color = request.form.get('bg_color', '#ffffff')
            trust_result = None
            is_url = re.match(r'^https?://', data.strip())
            if is_url:
                trust_result = check_url_trust(data.strip())
            else:
                trust_result = {'score': 'safe', 'icon': '✅', 'reason': 'No issues detected', 'url': data.strip()}
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color=qr_color, back_color=bg_color).convert("RGBA")
            if 'logo' in request.files and request.files['logo'].filename:
                logo_file = request.files['logo']
                img = embed_logo(img, logo_file)
            img_io = BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)
            qr_img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
            # --- Backend QR decode for verification ---
            img_io.seek(0)
            decoded_data = None
            try:
                decoded = decode(Image.open(img_io))
                if decoded:
                    decoded_data = decoded[0].data.decode('utf-8')
            except Exception:
                decoded_data = None
            # Re-run trust check on decoded data if it's a URL
            decoded_trust_result = None
            if decoded_data and re.match(r'^https?://', decoded_data.strip()):
                decoded_trust_result = check_url_trust(decoded_data.strip())
            return render_template('index.html',
                qr_img_base64=qr_img_base64,
                text=data,
                decoded_data=decoded_data,
                decoded_trust_result=decoded_trust_result,
                nature_labels=NATURE_LABELS,
                qr_color=qr_color,
                bg_color=bg_color,
                trust_result=trust_result
            )
    # On GET, do not show any QR codes
    return render_template('index.html', qr_img_base64=None, multi_qr_results=None, nature_labels=NATURE_LABELS)

# --- Anti-Scam URL Validator ---
def check_url_trust(url):
    reason = []
    score = 'safe'
    # Pattern-based checks
    if '@' in url:
        reason.append('Contains @')
        score = 'suspicious'
    if 'xn--' in url:
        reason.append('Punycode domain')
        score = 'suspicious'
    if re.search(r'\.zip$|\.exe$|\.scr$|\.bat$', url):
        reason.append('Suspicious file extension')
        score = 'dangerous'
    if re.search(r'http.*http', url):
        reason.append('Nested http')
        score = 'dangerous'
    if url.startswith('http://'):
        reason.append('HTTP link (not secure)')
        score = 'suspicious'
    # Shortener expansion
    shorteners = ['bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly', 'is.gd', 'buff.ly']
    if any(s in url for s in shorteners):
        try:
            resp = requests.head(url, allow_redirects=True, timeout=3)
            expanded = resp.url
            if expanded != url:
                url = expanded
                reason.append(f'Expanded to {expanded}')
        except Exception:
            reason.append('Could not expand shortener')
            score = 'suspicious'
    # Google Safe Browsing API (optional)
    GSB_API_KEY = os.environ.get('GSB_API_KEY')
    if GSB_API_KEY:
        try:
            gsb_resp = requests.post(
                'https://safebrowsing.googleapis.com/v4/threatMatches:find?key=' + GSB_API_KEY,
                json={
                    "client": {"clientId": "qrgen-app", "clientVersion": "1.0"},
                    "threatInfo": {
                        "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                        "platformTypes": ["ANY_PLATFORM"],
                        "threatEntryTypes": ["URL"],
                        "threatEntries": [{"url": url}]
                    }
                }, timeout=3
            )
            if gsb_resp.json().get('matches'):
                reason.append('Google Safe Browsing flagged')
                score = 'dangerous'
        except Exception:
            reason.append('GSB check failed')
    # Local trust fallback
    if not re.match(r'^https://', url):
        score = 'suspicious'
        reason.append('Not HTTPS')
    # Domain check (basic)
    trusted_domains = ['github.com', 'google.com', 'wikipedia.org', 'microsoft.com']
    if not any(d in url for d in trusted_domains):
        reason.append('Unrecognized domain')
        if score == 'safe':
            score = 'suspicious'
    # Finalize
    if score == 'dangerous':
        icon = '🚫'
    elif score == 'suspicious':
        icon = '⚠️'
    else:
        icon = '✅'
    return {'score': score, 'icon': icon, 'reason': ', '.join(reason) or 'No issues detected', 'url': url}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
