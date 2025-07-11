
"""
QRglyph Routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, current_app
from .utils import generate_qr, decode_qr, trust_check, expand_url
from PIL import Image
import io
import base64

main_bp = Blueprint('main', __name__)

# Single QR Generation Route
@main_bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = request.form.get('qr-content')
        fill_color = request.form.get('qr-color', '#00ff00')
        back_color = request.form.get('bg-color', '#000000')
        logo_file = request.files.get('logo')
        logo_img = None
        if logo_file and logo_file.filename:
            logo_img = Image.open(logo_file.stream)
        img = generate_qr(data, fill_color=fill_color, back_color=back_color, logo_path=None if not logo_img else logo_img)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode('utf-8')
        decoded = decode_qr(img)
        trust = trust_check(decoded or '', gsb_api_key=current_app.config.get('GSB_API_KEY'))
        return render_template('index.html',
            qr_image=img_b64,
            decoded=decoded,
            trust=trust,
            form_data={
                'qr-content': data,
                'qr-color': fill_color,
                'bg-color': back_color
            }
        )
    return render_template('index.html')

# Multi QR Generation Route
@main_bp.route('/multi', methods=['GET', 'POST'])
def multi_qr():
    qr_results = []
    form_data = []
    num_qrs = 1
    if request.method == 'POST':
        try:
            num_qrs = int(request.form.get('num_qrs', 1))
        except Exception:
            num_qrs = 1
        num_qrs = max(1, min(10, num_qrs))
        for i in range(1, num_qrs+1):
            label = request.form.get(f'label_{i}', f'QR {i}')
            data = request.form.get(f'qr-content_{i}', '')
            color = request.form.get(f'qr-color_{i}', '#00ff00')
            form_data.append({'label': label, 'qr-content': data, 'qr-color': color})
            if data:
                img = generate_qr(data, fill_color=color, back_color='#000000')
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                buf.seek(0)
                img_b64 = base64.b64encode(buf.read()).decode('utf-8')
                decoded = decode_qr(img)
                trust = trust_check(decoded or '', gsb_api_key=current_app.config.get('GSB_API_KEY'))
                qr_results.append({
                    'label': label,
                    'qr_image': img_b64,
                    'decoded': decoded,
                    'trust': trust,
                    'color': color
                })
        while len(form_data) < num_qrs:
            form_data.append({'label': f'QR {len(form_data)+1}', 'qr-content': '', 'qr-color': '#00ff00'})
        return render_template('multi.html', qr_results=qr_results, form_data=form_data)
    # GET: default to 1 QR
    form_data = [{'label': 'QR 1', 'qr-content': '', 'qr-color': '#00ff00'}]
    return render_template('multi.html', qr_results=None, form_data=form_data)

# QR Verification Route
@main_bp.route('/verify', methods=['GET', 'POST'])
def verify_qr():
    result = None
    if request.method == 'POST':
        qr_file = request.files.get('qr-image')
        if qr_file and qr_file.filename:
            try:
                img = Image.open(qr_file.stream)
                decoded = decode_qr(img)
                trust = trust_check(decoded or '', gsb_api_key=current_app.config.get('GSB_API_KEY'))
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                buf.seek(0)
                img_b64 = base64.b64encode(buf.read()).decode('utf-8')
                result = {
                    'qr_image': img_b64,
                    'decoded': decoded,
                    'trust': trust
                }
            except Exception as e:
                result = {'error': f'Could not process image: {e}'}
        else:
            result = {'error': 'No image uploaded.'}
    return render_template('verify.html', result=result)

# Camera-based QR Verification Route
@main_bp.route('/verify/camera', methods=['GET', 'POST'])
def verify_camera():
    result = None
    if request.method == 'POST':
        qr_content = request.form.get('qr-content')
        if qr_content:
            trust = trust_check(qr_content, gsb_api_key=current_app.config.get('GSB_API_KEY'))
            result = {
                'decoded': qr_content,
                'trust': trust
            }
        else:
            result = {'error': 'No QR content received.'}
    return render_template('verify_camera.html', result=result)
