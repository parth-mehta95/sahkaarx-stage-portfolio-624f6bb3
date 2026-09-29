"""
app.py - Flask API delivering Registration and Login endpoints with password hashing.

Deliverables:
- POST /register : Registration endpoint with input validation and password hashing
- POST /login    : Login endpoint with hashed password validation
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from flask import Flask, jsonify, request, Response

from User import User
from Task import Task


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """
    Application factory creating and configuring the Flask app.

    Args:
        test_config: Optional dictionary with configuration overrides.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    if test_config:
        app.config.update(test_config)

    # ------------------------------------------------------------------
    # Deliverable 1: Registration endpoint
    # ------------------------------------------------------------------
    @app.route("/register", methods=["POST"])
    def register_endpoint() -> Tuple[Response, int]:
        """
        Register a new user account with secure password hashing.

        Expected JSON payload:
            {
                "username": "example_user",
                "email": "user@example.com",
                "password": "SecretPassword123"
            }

        Returns:
            201 Created on success with sanitized user details.
            400 Bad Request on missing fields, format errors, or duplicates.
        """
        data = request.get_json(silent=True)
        if data is None or not isinstance(data, dict):
            return jsonify({"error": "Request body must be a valid JSON object."}), 400

        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        # Field presence and type checks
        if not username or not isinstance(username, str) or not username.strip():
            return jsonify({"error": "Username is required and cannot be empty."}), 400

        if not email or not isinstance(email, str) or not email.strip() or "@" not in email:
            return jsonify({"error": "Valid email address is required."}), 400

        if not password or not isinstance(password, str) or not password.strip():
            return jsonify({"error": "Password is required and cannot be empty."}), 400

        clean_username = username.strip()
        clean_email = email.strip()

        # Check for duplicates before registration
        if User.get_by_username(clean_username) is not None:
            return jsonify({"error": f"Username '{clean_username}' is already taken."}), 400

        if User.get_by_email(clean_email) is not None:
            return jsonify({"error": f"Email '{clean_email}' is already registered."}), 400

        try:
            # Success criterion: Passwords hashed before storage
            user = User.register(
                username=clean_username,
                email=clean_email,
                password=password,
            )
            return jsonify({
                "message": "User registered successfully.",
                "user": user.to_dict(),
            }), 201
        except ValueError as val_err:
            return jsonify({"error": str(val_err)}), 400
        except Exception as exc:
            return jsonify({"error": f"Internal server error: {str(exc)}"}), 500

    # ------------------------------------------------------------------
    # Deliverable 2: Login endpoint with hashing
    # ------------------------------------------------------------------
    @app.route("/login", methods=["POST"])
    def login_endpoint() -> Tuple[Response, int]:
        """
        Authenticate a user by validating their password against stored hash.

        Expected JSON payload:
            {
                "username": "example_user",  # or email
                "password": "SecretPassword123"
            }

        Returns:
            200 OK on successful authentication.
            400 Bad Request on missing fields.
            401 Unauthorized on invalid credentials.
        """
        data = request.get_json(silent=True)
        if data is None or not isinstance(data, dict):
            return jsonify({"error": "Request body must be a valid JSON object."}), 400

        username = data.get("username")
        password = data.get("password")

        if not username or not isinstance(username, str) or not username.strip():
            return jsonify({"error": "Username is required."}), 400

        if not password or not isinstance(password, str) or not password.strip():
            return jsonify({"error": "Password is required."}), 400

        # Success criterion: Login validates hashed password
        user = User.login(username=username.strip(), password=password)
        if not user:
            return jsonify({"error": "Invalid username or password."}), 401

        return jsonify({
            "message": "Login successful.",
            "user": user.to_dict(),
        }), 200

    # ------------------------------------------------------------------
    # Additional task management routes leveraging User's tasks array
    # ------------------------------------------------------------------
    @app.route("/users/<string:username>", methods=["GET"])
    def get_user_profile(username: str) -> Tuple[Response, int]:
        """Retrieve user profile by username."""
        user = User.get_by_username(username)
        if not user:
            return jsonify({"error": f"User '{username}' not found."}), 404
        return jsonify(user.to_dict()), 200

    @app.route("/users/<string:username>/tasks", methods=["GET"])
    def get_user_tasks(username: str) -> Tuple[Response, int]:
        """Retrieve all tasks stored in the user's tasks array."""
        user = User.get_by_username(username)
        if not user:
            return jsonify({"error": f"User '{username}' not found."}), 404
        return jsonify([t.to_dict() if hasattr(t, "to_dict") else t for t in user.get_tasks()]), 200

    @app.route("/users/<string:username>/tasks", methods=["POST"])
    def add_user_task(username: str) -> Tuple[Response, int]:
        """Add a task into the user's tasks array."""
        user = User.get_by_username(username)
        if not user:
            return jsonify({"error": f"User '{username}' not found."}), 404

        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict) or not data.get("title"):
            return jsonify({"error": "Task title is required."}), 400

        new_task = Task(
            title=data["title"],
            description=data.get("description"),
            due_date=data.get("due_date"),
            user_id=user.id,
            task_id=len(user.tasks) + 1,
        )
        user.add_task(new_task)
        return jsonify(new_task.to_dict()), 201

    @app.route("/health", methods=["GET"])
    def health_check() -> Tuple[Response, int]:
        """Health check endpoint."""
        return jsonify({"status": "healthy"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
