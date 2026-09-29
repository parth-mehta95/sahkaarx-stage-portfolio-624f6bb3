"""
routes.py - Flask Routes Refactored with OOP Principles.

Demonstrates Clean Architecture & Delegation:
1. Flask routes do NOT contain inline authentication logic.
2. Route handlers delegate registration directly to User.register(username, password, email).
3. Route handlers delegate login/authentication directly to User.authenticate(username, password).
4. Password hashing, validation, and storage are fully encapsulated inside domain classes.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Union
from flask import Blueprint, Flask, Response, jsonify, make_response, request

from models import (
    AuthenticationError,
    Task,
    User,
    UserAlreadyExistsError,
    ValidationError,
)

# Create Blueprints
auth_bp = Blueprint("auth", __name__)
tasks_bp = Blueprint("tasks", __name__)


# =============================================================================
# Request Helper Functions
# =============================================================================

def get_request_data() -> Dict[str, Any]:
    """
    Extract payload data seamlessly from JSON or form-encoded requests.

    Returns:
        Dict[str, Any]: Parsed request dictionary.
    """
    if request.is_json:
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            return payload
        return {}

    # Handle form data if submitted via HTML form or urlencoded
    if request.form:
        return dict(request.form)

    # Fallback to json if raw data is present
    try:
        data = request.get_json(force=True, silent=True)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return {}


# =============================================================================
# Authentication Routes (Delegating to User Class Methods)
# =============================================================================

@auth_bp.route("/register", methods=["POST"])
def register() -> Tuple[Response, int]:
    """
    User Registration Endpoint.

    OOP Refactoring:
    - Inline hashing and validation have been extracted.
    - All registration logic is delegated to `User.register(username, password, email)`.

    Responses:
        201 Created: User created successfully.
        400 Bad Request: Missing or invalid username/password.
        409 Conflict: Username or email already registered.
    """
    data = get_request_data()

    username = data.get("username")
    password = data.get("password")
    email = data.get("email", "")

    # Ensure required fields are provided
    if not username or not str(username).strip():
        return jsonify({"error": "Username is required.", "status_code": 400}), 400

    if not password or not str(password):
        return jsonify({"error": "Password is required.", "status_code": 400}), 400

    try:
        # DELEGATION: User class method handles validation, hashing, and persistence
        user = User.register(
            username=str(username).strip(),
            password=str(password),
            email=str(email).strip() if email else "",
        )
        return jsonify({
            "message": "User registered successfully.",
            "user": user.to_dict(),
            "status_code": 201,
        }), 201

    except UserAlreadyExistsError as e:
        return jsonify({
            "error": str(e),
            "status_code": 409,
        }), 409

    except ValidationError as e:
        return jsonify({
            "error": str(e),
            "status_code": 400,
        }), 400

    except Exception as e:
        return jsonify({
            "error": f"An unexpected error occurred: {str(e)}",
            "status_code": 500,
        }), 500


@auth_bp.route("/login", methods=["POST"])
def login() -> Tuple[Response, int]:
    """
    User Login / Authentication Endpoint.

    OOP Refactoring:
    - Inline password hashing comparisons and query loops have been removed.
    - Route delegates entirely to `User.authenticate(username, password)`.

    Responses:
        200 OK: Authentication successful, user details returned.
        400 Bad Request: Missing username or password.
        401 Unauthorized: Invalid username or incorrect password.
    """
    data = get_request_data()

    username = data.get("username")
    password = data.get("password")

    if not username or not str(username).strip():
        return jsonify({"error": "Username is required.", "status_code": 400}), 400

    if not password or not str(password):
        return jsonify({"error": "Password is required.", "status_code": 400}), 400

    # DELEGATION: User class encapsulates credential lookup & cryptographic hash check
    user = User.authenticate(username=str(username).strip(), password=str(password))

    if user is None:
        return jsonify({
            "error": "Invalid username or password.",
            "status_code": 401,
        }), 401

    return jsonify({
        "message": "Login successful.",
        "user": user.to_dict(),
        "status_code": 200,
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout() -> Tuple[Response, int]:
    """Logout endpoint."""
    return jsonify({
        "message": "Logged out successfully.",
        "status_code": 200,
    }), 200


@auth_bp.route("/users", methods=["GET"])
def get_all_users() -> Tuple[Response, int]:
    """Retrieve all users (sanitized, password hashes never exposed)."""
    users = User.get_all()
    return jsonify({
        "users": [user.to_dict() for user in users],
        "count": len(users),
        "status_code": 200,
    }), 200


@auth_bp.route("/users/<username>", methods=["GET"])
def get_user_by_username(username: str) -> Tuple[Response, int]:
    """Retrieve a single user by username."""
    user = User.get_by_username(username)
    if user is None:
        return jsonify({"error": f"User '{username}' not found.", "status_code": 404}), 404

    return jsonify({
        "user": user.to_dict(include_tasks=True),
        "status_code": 200,
    }), 200


# =============================================================================
# Task Routes (Delegating to Task & User Domain Methods)
# =============================================================================

@tasks_bp.route("/tasks", methods=["GET"])
def list_tasks() -> Tuple[Response, int]:
    """List tasks, optionally filtered by user_id or status."""
    user_id = request.args.get("user_id")
    status = request.args.get("status")

    tasks = Task.get_all()

    if user_id:
        tasks = [t for t in tasks if t.user_id == str(user_id)]
    if status:
        tasks = [t for t in tasks if t.status.lower() == status.lower()]

    return jsonify({
        "tasks": [t.to_dict() for t in tasks],
        "count": len(tasks),
        "status_code": 200,
    }), 200


@tasks_bp.route("/tasks", methods=["POST"])
def create_task() -> Tuple[Response, int]:
    """Create a new task delegating to Task.create() or User.create_task()."""
    data = get_request_data()
    title = data.get("title") or data.get("name")

    if not title or not str(title).strip():
        return jsonify({"error": "Task title is required.", "status_code": 400}), 400

    user_id = data.get("user_id")
    if user_id:
        user = User.get_by_id(user_id)
        if user:
            task = user.create_task(
                title=str(title).strip(),
                description=str(data.get("description", "")),
                status=str(data.get("status", "pending")),
            )
            return jsonify({"message": "Task created.", "task": task.to_dict(), "status_code": 201}), 201

    task = Task.create(
        title=str(title).strip(),
        description=str(data.get("description", "")),
        status=str(data.get("status", "pending")),
        user_id=user_id,
    )
    return jsonify({"message": "Task created.", "task": task.to_dict(), "status_code": 201}), 201


@tasks_bp.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id: str) -> Tuple[Response, int]:
    """Retrieve single task by ID."""
    task = Task.get_by_id(task_id)
    if task is None:
        return jsonify({"error": f"Task '{task_id}' not found.", "status_code": 404}), 404
    return jsonify({"task": task.to_dict(), "status_code": 200}), 200


@tasks_bp.route("/tasks/<task_id>", methods=["PUT", "PATCH"])
def update_task(task_id: str) -> Tuple[Response, int]:
    """Update task by ID."""
    task = Task.get_by_id(task_id)
    if task is None:
        return jsonify({"error": f"Task '{task_id}' not found.", "status_code": 404}), 404

    data = get_request_data()
    try:
        task.update(**data)
        return jsonify({"message": "Task updated.", "task": task.to_dict(), "status_code": 200}), 200
    except ValidationError as e:
        return jsonify({"error": str(e), "status_code": 400}), 400


@tasks_bp.route("/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id: str) -> Tuple[Response, int]:
    """Delete task by ID."""
    deleted = Task.delete_by_id(task_id)
    if not deleted:
        return jsonify({"error": f"Task '{task_id}' not found.", "status_code": 404}), 404
    return jsonify({"message": f"Task '{task_id}' deleted successfully.", "status_code": 200}), 200


# =============================================================================
# Application Factory
# =============================================================================

def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """
    Factory to construct and configure the Flask application.
    Registers both root endpoints and prefixed blueprint endpoints.
    """
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    if test_config:
        app.config.update(test_config)

    # Register blueprints with and without prefix for flexible API consumer support
    app.register_blueprint(auth_bp, url_prefix="")
    app.register_blueprint(auth_bp, url_prefix="/auth", name="auth_prefixed")
    app.register_blueprint(tasks_bp)

    # Global HTTP error handlers
    @app.errorhandler(400)
    def bad_request(error: Any) -> Tuple[Response, int]:
        return jsonify({"error": "Bad Request", "status_code": 400}), 400

    @app.errorhandler(401)
    def unauthorized(error: Any) -> Tuple[Response, int]:
        return jsonify({"error": "Unauthorized", "status_code": 401}), 401

    @app.errorhandler(404)
    def not_found(error: Any) -> Tuple[Response, int]:
        return jsonify({"error": "Resource Not Found", "status_code": 404}), 404

    @app.errorhandler(405)
    def method_not_allowed(error: Any) -> Tuple[Response, int]:
        return jsonify({"error": "Method Not Allowed", "status_code": 405}), 405

    @app.errorhandler(500)
    def internal_error(error: Any) -> Tuple[Response, int]:
        return jsonify({"error": "Internal Server Error", "status_code": 500}), 500

    return app


# Default application instance for quick imports
app = create_app()
