"""
app.py - Main Application Entrypoint for Task Manager Authentication System.

Runs the Flask development server and provides create_app factory.
"""

from __future__ import annotations

import os
from routes import app, create_app

__all__ = ["app", "create_app"]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development" or os.environ.get("FLASK_DEBUG") == "1"
    print(f"Starting Task Manager Authentication Server on http://127.0.0.1:{port} (debug={debug})...")
    app.run(host="0.0.0.0", port=port, debug=debug)
