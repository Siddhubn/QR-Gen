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
    if logo_path:
        try:
            logo = Image.open(logo_path)
            box = (img.size[0]//3, img.size[1]//3, 2*img.size[0]//3, 2*img.size[1]//3)
            logo = logo.resize((box[2]-box[0], box[3]-box[1]))
            img.paste(logo, box[:2], mask=logo if logo.mode=='RGBA' else None)
        except Exception:
            pass
    return img

def decode_qr(image):
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

def trust_check(content, gsb_api_key=None):
    # Pattern-based checks
    reasons = []
    score = 'safe'
    url_pattern = re.compile(r'https?://[\w\.-]+')
    urls = url_pattern.findall(content)
    debug = os.getenv('DEBUG_TRUST_CHECK', '0') == '1'
    for url in urls:
        if 'bit.ly' in url or 'tinyurl' in url or 't.co' in url:
            reasons.append('Shortened URL detected')
            url = expand_url(url)
        if not url.startswith('https://'):
            reasons.append('Non-HTTPS URL')
            score = 'suspicious'
        if re.search(r'\.(exe|scr|zip|bat|js|vbs|jar|apk|msi|dll)$', url):
            reasons.append('Suspicious file extension')
            score = 'dangerous'
        if 'http://' in url[8:]:
            reasons.append('Nested http found')
            score = 'dangerous'
    # Google Safe Browsing
    if gsb_api_key and urls:
        for url in urls:
            gsb_result, gsb_log = check_gsb(url, gsb_api_key, debug=debug)
            if debug:
                print(f"[GSB] URL: {url}\n[GSB] Result: {gsb_result}\n[GSB] Log: {gsb_log}")
            if gsb_result == 'dangerous':
                reasons.append('Google Safe Browsing flagged this URL')
                score = 'dangerous'
            elif gsb_result == 'suspicious' and score != 'dangerous':
                reasons.append('Google Safe Browsing: suspicious')
                score = 'suspicious'
    if not reasons:
        reasons.append('No issues detected')
    icon = {'safe': '✅', 'suspicious': '⚠️', 'dangerous': '🚫'}[score]
    # Always include a 'details' field for template safety
    details = {
        'urls': urls,
        'reasons': reasons,
        'gsb_api_key_used': bool(gsb_api_key),
        'gsb_results': [check_gsb(url, gsb_api_key, debug=debug)[0] if gsb_api_key else None for url in urls] if urls else [],
    }
    return {'score': score, 'icon': icon, 'reasons': reasons, 'details': details}

def check_gsb(url, api_key, debug=False):
    # Google Safe Browsing API check
    try:
        api_url = 'https://safebrowsing.googleapis.com/v4/threatMatches:find?key=' + api_key
        body = {
            "client": {"clientId": "qrglyph", "clientVersion": "1.0"},
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url}]
            }
        }
        resp = requests.post(api_url, json=body, timeout=5)
        log = {
            'status_code': resp.status_code,
            'response': resp.json() if resp.content else None
        }
        if resp.status_code == 200 and resp.json().get('matches'):
            return 'dangerous', log
        return 'safe', log
    except Exception as e:
        log = {'error': str(e)}
        return 'suspicious', log
