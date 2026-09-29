"""app.py - Flask application factory and entry point."""
from __future__ import annotations

from typing import Optional
from flask import Flask
from models import db
from routes import api_bp


def create_app(database_uri: Optional[str] = None) -> Flask:
    """Create and configure the Flask application."""
    app: Flask = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri or "sqlite:///task_manager.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app: Flask = create_app()
    app.run(debug=True, port=5000)
