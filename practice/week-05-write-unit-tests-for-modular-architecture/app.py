"""
app.py - Main Application Entrypoint for Task Manager Application.

Separation of Concerns:
This module acts as the application assembler:
- Imports domain models from models.py
- Imports route blueprints from routes.py
- Imports utility functions from utils.py
- Configures and boots the Flask application
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from flask import Flask, Response, jsonify

# Ensure local imports resolve whether imported as package or top-level module
current_dir = str(Path(__file__).resolve().parent)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from models import Task, User
    from routes import auth_bp, register_routes, tasks_bp
    from utils import error_response, json_response
except ImportError:  # pragma: no cover
    from .models import Task, User
    from .routes import auth_bp, register_routes, tasks_bp
    from .utils import error_response, json_response

__all__ = ["app", "create_app", "User", "Task", "auth_bp", "tasks_bp"]


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """
    Application factory to create and configure the Flask app.

    Args:
        test_config: Optional dictionary containing configuration overrides for testing.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    if test_config:
        app.config.update(test_config)

    # Register routes and blueprints
    register_routes(app)

    # Root discovery / health check endpoint
    @app.route("/", methods=["GET"])
    def index() -> Tuple[Response, int]:
        return json_response(
            {
                "service": "Task Manager Modular REST API",
                "architecture": "Separation of Concerns (models, routes, utils, app)",
                "endpoints": {
                    "auth": ["/register", "/login", "/logout", "/users", "/users/<username>"],
                    "tasks": ["/tasks", "/tasks/<task_id>"],
                },
            },
            status_code=200,
            message="Task Manager API is running.",
        )

    # Centralized HTTP Error Handlers
    @app.errorhandler(400)
    def bad_request(error: Any) -> Tuple[Response, int]:
        return error_response("Bad Request", 400)

    @app.errorhandler(401)
    def unauthorized(error: Any) -> Tuple[Response, int]:
        return error_response("Unauthorized", 401)

    @app.errorhandler(404)
    def not_found(error: Any) -> Tuple[Response, int]:
        return error_response("Resource Not Found", 404)

    @app.errorhandler(405)
    def method_not_allowed(error: Any) -> Tuple[Response, int]:
        return error_response("Method Not Allowed", 405)

    @app.errorhandler(500)
    def internal_error(error: Any) -> Tuple[Response, int]:
        return error_response("Internal Server Error", 500)

    return app


# Default application instance for WSGI servers & test runners
app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development" or os.environ.get("FLASK_DEBUG") == "1"
    print(f"Starting Task Manager on http://127.0.0.1:{port} (debug={debug})...")
    app.run(host="0.0.0.0", port=port, debug=debug)
