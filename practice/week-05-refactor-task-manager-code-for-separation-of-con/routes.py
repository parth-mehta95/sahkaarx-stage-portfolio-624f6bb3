"""
routes.py - Flask Route Handlers for Task Manager Application.

Separation of Concerns:
All HTTP route handlers are centralized in this module:
1. Authentication Endpoints: /register, /login, /logout, /users, /users/<username>
2. Task CRUD Endpoints: /tasks, /tasks/<task_id> (GET, POST, PUT, PATCH, DELETE)
All business logic is delegated to models.py and helper functions to utils.py.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union
from flask import Blueprint, Flask, Response, jsonify, request

from models import (
    AuthenticationError,
    NotFoundError,
    Task,
    User,
    UserAlreadyExistsError,
    ValidationError,
)
from utils import (
    error_response,
    get_request_data,
    json_response,
)

# Define Flask Blueprints
auth_bp = Blueprint("auth", __name__)
tasks_bp = Blueprint("tasks", __name__)


# =============================================================================
# 1. Authentication Route Handlers (auth_bp)
# =============================================================================

@auth_bp.route("/register", methods=["POST"])
def register() -> Tuple[Response, int]:
    """
    Register a new user account.

    Delegation:
    - Input extraction: utils.get_request_data()
    - Registration logic & hashing: User.register(...)
    """
    data = get_request_data()

    username = data.get("username")
    password = data.get("password")
    email = data.get("email", "")

    if not username:
        return error_response("Username is required.", 400)
    if not password:
        return error_response("Password is required.", 400)

    try:
        user = User.register(
            username=str(username),
            password=str(password),
            email=str(email) if email else "",
        )
        return json_response(
            {"user": user.to_dict()},
            status_code=201,
            message="User registered successfully.",
        )
    except UserAlreadyExistsError as e:
        return error_response(str(e), 409)
    except ValidationError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f"An unexpected error occurred: {str(e)}", 500)


@auth_bp.route("/login", methods=["POST"])
def login() -> Tuple[Response, int]:
    """
    Authenticate an existing user.

    Delegation:
    - Validation and verification: User.authenticate(...)
    """
    data = get_request_data()

    username = data.get("username")
    password = data.get("password")

    if not username:
        return error_response("Username is required.", 400)
    if not password:
        return error_response("Password is required.", 400)

    user = User.authenticate(username=str(username), password=str(password))
    if user is None:
        return error_response("Invalid username or password.", 401)

    return json_response(
        {"user": user.to_dict()},
        status_code=200,
        message="Login successful.",
    )


@auth_bp.route("/logout", methods=["POST"])
def logout() -> Tuple[Response, int]:
    """Log out current user session."""
    return json_response(status_code=200, message="Logged out successfully.")


@auth_bp.route("/users", methods=["GET"])
def get_users() -> Tuple[Response, int]:
    """Retrieve list of all registered users without exposing credentials."""
    users = User.get_all()
    return json_response(
        {
            "users": [u.to_dict() for u in users],
            "count": len(users),
        },
        status_code=200,
    )


@auth_bp.route("/users/<username>", methods=["GET"])
def get_user_by_username(username: str) -> Tuple[Response, int]:
    """Retrieve details for a single user by username."""
    user = User.get_by_username(username)
    if user is None:
        return error_response(f"User '{username}' not found.", 404)

    return json_response(
        {"user": user.to_dict(include_tasks=True)},
        status_code=200,
    )


# =============================================================================
# 2. Task CRUD Route Handlers (tasks_bp)
# =============================================================================

@tasks_bp.route("/tasks", methods=["GET"])
def list_tasks() -> Tuple[Response, int]:
    """
    List all tasks, with optional query filtering by status or user_id.
    """
    user_id = request.args.get("user_id")
    status = request.args.get("status")

    tasks = Task.get_all()

    if user_id:
        tasks = [t for t in tasks if t.user_id == str(user_id)]
    if status:
        tasks = [t for t in tasks if t.status.lower() == str(status).strip().lower()]

    return json_response(
        {
            "tasks": [t.to_dict() for t in tasks],
            "count": len(tasks),
        },
        status_code=200,
    )


@tasks_bp.route("/tasks", methods=["POST"])
def create_task() -> Tuple[Response, int]:
    """
    Create a new task record.

    Delegation:
    - Task instantiation and registration: Task.create(...) or User.create_task(...)
    """
    data = get_request_data()
    title = data.get("title") or data.get("name")

    if not title or not str(title).strip():
        return error_response("Task title is required.", 400)

    description = str(data.get("description", ""))
    status = str(data.get("status", "pending"))
    user_id = data.get("user_id")

    try:
        if user_id:
            user = User.get_by_id(user_id)
            if user:
                task = user.create_task(title=str(title).strip(), description=description, status=status)
                return json_response(
                    {"task": task.to_dict()},
                    status_code=201,
                    message="Task created successfully.",
                )

        task = Task.create(
            title=str(title).strip(),
            description=description,
            status=status,
            user_id=user_id,
        )
        return json_response(
            {"task": task.to_dict()},
            status_code=201,
            message="Task created successfully.",
        )
    except ValidationError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f"An unexpected error occurred: {str(e)}", 500)


@tasks_bp.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id: str) -> Tuple[Response, int]:
    """Retrieve a single task by ID."""
    task = Task.get_by_id(task_id)
    if task is None:
        return error_response(f"Task '{task_id}' not found.", 404)

    return json_response({"task": task.to_dict()}, status_code=200)


@tasks_bp.route("/tasks/<task_id>", methods=["PUT", "PATCH"])
def update_task(task_id: str) -> Tuple[Response, int]:
    """Update task details by ID."""
    task = Task.get_by_id(task_id)
    if task is None:
        return error_response(f"Task '{task_id}' not found.", 404)

    data = get_request_data()
    if not data:
        return error_response("No update fields provided.", 400)

    try:
        task.update(**data)
        return json_response(
            {"task": task.to_dict()},
            status_code=200,
            message="Task updated successfully.",
        )
    except ValidationError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f"An unexpected error occurred: {str(e)}", 500)


@tasks_bp.route("/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id: str) -> Tuple[Response, int]:
    """Delete a task by ID."""
    deleted = Task.delete_by_id(task_id)
    if not deleted:
        return error_response(f"Task '{task_id}' not found.", 404)

    return json_response(
        status_code=200,
        message=f"Task '{task_id}' deleted successfully.",
    )


# =============================================================================
# Helper to register all blueprints on a Flask application
# =============================================================================

def register_routes(app: Flask) -> None:
    """Register all modular route blueprints on the Flask app."""
    # Register blueprints at root and optional prefixes for maximum flexibility
    app.register_blueprint(auth_bp, url_prefix="")
    app.register_blueprint(auth_bp, url_prefix="/auth", name="auth_prefixed")
    app.register_blueprint(tasks_bp, url_prefix="")
    app.register_blueprint(tasks_bp, url_prefix="/api", name="tasks_prefixed")
