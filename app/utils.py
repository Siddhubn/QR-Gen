"""
QRglyph Utility Functions
"""
import qrcode
from PIL import Image
from pyzbar.pyzbar import decode
import requests
import re
import os
import logging

def generate_qr(data, fill_color='black', back_color='white', logo_path=None):
    # Generate QR code with optional logo
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill_color, back_color=back_color).convert('RGB')
    if logo_path is not None:
        try:
            # If logo_path is a PIL Image, use it directly; else open as file path
            if isinstance(logo_path, Image.Image):
                logo = logo_path
            else:
                logo = Image.open(logo_path)
            # Resize logo to fit in the center (max 1/3 of QR size)
            qr_w, qr_h = img.size
            logo_size = min(qr_w, qr_h) // 3
            logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
            # Center the logo
            pos = ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2)
            if logo.mode in ('RGBA', 'LA'):
                img.paste(logo, pos, mask=logo)
            else:
                img.paste(logo, pos)
        except Exception as e:
            logging.warning(f"Logo embedding failed: {e}")
    return img

def decode_qr(image):
    # Decode QR code from PIL Image
    decoded = decode(image)
    if decoded:
        return decoded[0].data.decode('utf-8')
    return None
    # Decode QR code from PIL Image
    decoded = decode(image)
    if decoded:
        return decoded[0].data.decode('utf-8')
    return None

def expand_url(url):
    # Expand shortened URLs
    try:
        resp = requests.head(url, allow_redirects=True, timeout=5)
        return resp.url
    except Exception:
        return url

def trust_check(content):
    # Advanced local trust scoring algorithm (no APIs)
    reasons = []
    score = 'safe'
    url_pattern = re.compile(r'https?://[\w\.-]+')
    urls = url_pattern.findall(content)
    suspicious_keywords = [
        'login', 'verify', 'update', 'secure', 'account', 'bank', 'paypal', 'confirm', 'signin', 'webscr',
        'security', 'ebay', 'apple', 'amazon', 'dropbox', 'wallet', 'crypto', 'blockchain', 'password', 'reset',
        'admin', 'support', 'alert', 'invoice', 'payment', 'gift', 'bonus', 'free', 'prize', 'urgent', 'win', 'winner'
    ]
    homoglyphs = {'\u0430': 'a', '\u0435': 'e', '\u0456': 'i', '\u043e': 'o', '\u0440': 'p', '\u0441': 'c', '\u0445': 'x', '\u0443': 'y', '\u0451': 'e', '\u04cf': 'l'}
    shorteners = ['bit.ly', 'tinyurl', 't.co', 'goo.gl', 'ow.ly', 'buff.ly', 'is.gd', 'cutt.ly', 'shorte.st', 'adf.ly', 'rebrand.ly']
    for url in urls:
        # Shortened URLs (must match domain exactly)
        for short in shorteners:
            if re.match(r'https?://'+re.escape(short)+r'(/|$)', url):
                reasons.append('Shortened URL detected')
                score = 'suspicious'
                break
        # Non-HTTPS
        if not url.startswith('https://'):
            reasons.append('Non-HTTPS URL')
            score = 'suspicious'
        # Suspicious file extensions
        if re.search(r'\.(exe|scr|zip|bat|js|vbs|jar|apk|msi|dll|php|asp|aspx|pif|com|cmd|cpl|jar|gadget|wsf|lnk|sh|bin|dat|run|msu|ps1|vb|vbe|vbs|ws|wsf|wsh)$', url):
            reasons.append('Suspicious file extension')
            score = 'dangerous'
        # Nested http
        if 'http://' in url[8:]:
            reasons.append('Nested http found')
            score = 'dangerous'
        # Excessive subdomains
        domain_parts = url.split('//')[-1].split('/')[0].split('.')
        if len(domain_parts) > 4:
            reasons.append('Excessive subdomains (possible masking)')
            score = 'suspicious'
        # Suspicious keywords
        if any(kw in url.lower() for kw in suspicious_keywords):
            reasons.append('Suspicious keyword in URL')
            score = 'suspicious'
        # Homoglyph/homograph attack detection
        if any(char in url for char in homoglyphs):
            reasons.append('Possible homograph attack (unicode lookalike)')
            score = 'dangerous'
        # Long URLs
        if len(url) > 100:
            reasons.append('Unusually long URL')
            score = 'suspicious'
        # IP address in URL
        if re.match(r'https?://\d+\.\d+\.\d+\.\d+', url):
            reasons.append('URL uses IP address instead of domain')
            score = 'suspicious'
    if not reasons:
        reasons.append('No issues detected')
    # Use only valid Unicode codepoints for icon (no surrogates)
    icon_map = {
        'safe': '\u2705',           # ✅
        'suspicious': '\u26a0',     # ⚠
        'dangerous': '\u274C'       # ❌
    }
    icon = icon_map[score]
    details = {
        'urls': urls,
        'reasons': reasons,
    }
    return {'score': score, 'icon': icon, 'reasons': reasons, 'details': details}
    
    