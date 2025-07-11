# QRglyph

A modular, production-ready Flask web application for generating, decoding, and verifying QR codes with anti-scam trust checks.

## Features
- Single and multi QR generation with color and logo options
- QR decoding and anti-scam trust check (pattern-based, shortener expansion, Google Safe Browsing)
- QR verification via upload or camera
- Modern, hacker-inspired UI (responsive, accessible)
- Text-to-speech and sharing options for QR content
- Secure: uses environment variables for secrets
- Production-ready: Gunicorn, requirements.txt, render.yaml

## Setup
1. **Clone the repo:**
   ```bash
   git clone https://github.com/Siddhubn/QR-Gen.git
   cd QR-Gen
   ```
2. **Create a virtual environment and install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Configure environment variables:**
   - Copy `.env.example` to `.env` and set your `SECRET_KEY` (and `GSB_API_KEY` if available).

4. **Run locally:**
   ```bash
   flask run
   # or
   python app.py
   ```

5. **Production (Gunicorn):**
   ```bash
   gunicorn -w 4 -b 0.0.0.0:10000 app:app
   ```

6. **Deploy on Render:**
   - Use the included `render.yaml` for one-click deployment.

## Project Structure
```
QR-Gen/
├── app/
│   ├── __init__.py
│   ├── routes.py
│   ├── utils.py
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── style.css
│       └── main.js
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── render.yaml
└── README.md
```

## License
MIT
