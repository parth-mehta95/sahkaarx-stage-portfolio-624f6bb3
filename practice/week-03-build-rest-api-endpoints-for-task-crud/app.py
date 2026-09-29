"""
app.py - Flask Application Entrypoint for Task Manager REST API.

Provides:
- Flask application instance
- Application factory create_app()
- Route registration from routes.py
- Production / Development server startup
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional
from routes import app, create_app, tasks_bp

__all__ = ["app", "create_app", "tasks_bp"]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development" or os.environ.get("FLASK_DEBUG") == "1"
    print(f"Starting Task Manager REST API server on http://127.0.0.1:{port} (debug={debug})...")
    app.run(host="0.0.0.0", port=port, debug=debug)
