"""app.py - Flask application with SQLAlchemy ORM and SQLite configuration."""
from __future__ import annotations

import os
from typing import Optional
from flask import Flask, jsonify
from models import db, User, Task

DB_FILENAME = "task_manager.db"
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(CURRENT_DIR, DB_FILENAME)


def create_app(database_uri: Optional[str] = None) -> Flask:
    """Application factory for Task Manager Flask app."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri or f"sqlite:///{DEFAULT_DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize SQLAlchemy with the Flask app
    db.init_app(app)

    # Create tables automatically inside application context
    with app.app_context():
        db.create_all()

    @app.route("/")
    def index():
        return jsonify({
            "message": "Task Manager SQLite + SQLAlchemy ORM API",
            "database": app.config["SQLALCHEMY_DATABASE_URI"],
            "endpoints": {
                "users": "/api/users",
                "tasks": "/api/tasks",
            },
        })

    @app.route("/api/users", methods=["GET"])
    def get_users():
        users = User.query.all()
        return jsonify([u.to_dict() for u in users])

    @app.route("/api/tasks", methods=["GET"])
    def get_tasks():
        tasks = Task.query.all()
        return jsonify([t.to_dict() for t in tasks])

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
