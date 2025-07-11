"""
QRglyph Flask App Factory
"""
import os
from flask import Flask
from dotenv import load_dotenv

def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    app.config['GSB_API_KEY'] = os.getenv('GSB_API_KEY')

    from .routes import main_bp
    app.register_blueprint(main_bp)
    return app
