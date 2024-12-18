from flask import Flask
from app.api import api_bp

def create_app():
    """Создание приложения Flask."""
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    return app
