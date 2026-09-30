"""
routes.py - Fully Type-Hinted Flask Route Handlers for Task Manager Application.

Deliverables:
- Type-hinted routes and blueprint controllers.
- Complete separation of concerns:
  1. auth_bp: /register, /login, /logout, /users, /users/<username>
  2. tasks_bp: /tasks, /tasks/<task_id> (GET, POST, PUT, PATCH, DELETE)
- Delegates business rules to models.py and services.py, and request/response
  normalization to utils.py.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from flask import Blueprint, Flask, Response, jsonify, request

# Ensure local imports resolve whether imported as package or top-level module
current_dir: str = str(Path(__file__).resolve().parent)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from models import (
        AuthenticationError,
        NotFoundError,
        Task,
        User,
        UserAlreadyExistsError,
        ValidationError,
    )
    from services import TaskService, UserService
    from utils import (
        error_response,
        get_request_data,
        json_response,
    )
except ImportError:  # pragma: no cover
    from .models import (
        AuthenticationError,
        NotFoundError,
        Task,
        User,
        UserAlreadyExistsError,
        ValidationError,
    )
    from .services import TaskService, UserService
    from .utils import (
        error_response,
        get_request_data,
        json_response,
    )

# Define Flask Blueprints
auth_bp: Blueprint = Blueprint("auth", __name__)
tasks_bp: Blueprint = Blueprint("tasks", __name__)


# =============================================================================
# 1. Authentication Route Handlers (auth_bp)
# =============================================================================

@auth_bp.route("/register", methods=["POST"])
def register() -> Tuple[Response, int]:
    """
    Register a new user account with complete type annotations.

    Delegation:
    - Input extraction: utils.get_request_data()
    - Registration logic & hashing: UserService.register_user(...)
    """
    data: Dict[str, Any] = get_request_data()
    username: Any = data.get("username")
    password: Any = data.get("password")
    email: Any = data.get("email")

    if not username:
        return error_response("Username is required.", 400)
    if not password:
        return error_response("Password is required.", 400)
    if not email:
        return error_response("Email is required.", 400)

    try:
        user: User = UserService.register_user(
            username=str(username),
            email=str(email),
            password=str(password),
        )
        return json_response(
            {"user": user.to_dict()},
            status_code=201,
            message=f"User '{user.username}' registered successfully.",
        )
    except ValidationError as e:
        return error_response(str(e), 400)
    except UserAlreadyExistsError as e:
        return error_response(str(e), 409)
    except Exception as e:  # pragma: no cover
        return error_response(f"Internal registration error: {str(e)}", 500)


@auth_bp.route("/login", methods=["POST"])
def login() -> Tuple[Response, int]:
    """
    Authenticate user credentials and start session.

    Delegation:
    - Authentication logic: UserService.authenticate_user(...)
    """
    data: Dict[str, Any] = get_request_data()
    username: Any = data.get("username")
    password: Any = data.get("password")

    if not username or not password:
        return error_response("Both username and password are required.", 400)

    user: Optional[User] = UserService.authenticate_user(
        username=str(username),
        password=str(password),
    )

    if user is None:
        return error_response("Invalid username or password.", 401)

    return json_response(
        {
            "user": user.to_dict(),
            "authenticated": True,
        },
        status_code=200,
        message="Login successful.",
    )


@auth_bp.route("/logout", methods=["POST"])
def logout() -> Tuple[Response, int]:
    """Logout current user session."""
    return json_response(
        {"authenticated": False},
        status_code=200,
        message="Logout successful.",
    )


@auth_bp.route("/users", methods=["GET"])
def list_users() -> Tuple[Response, int]:
    """Retrieve list of all registered users."""
    users: List[User] = UserService.list_users()
    return json_response(
        {
            "users": [u.to_dict() for u in users],
            "count": len(users),
        },
        status_code=200,
    )


@auth_bp.route("/users/<username>", methods=["GET"])
def get_user_profile(username: str) -> Tuple[Response, int]:
    """Retrieve profile and tasks for a specific username."""
    user: Optional[User] = UserService.get_user_by_username(username)
    if user is None:
        return error_response(f"User '{username}' not found.", 404)

    return json_response(
        {"user": user.to_dict(include_tasks=True)},
        status_code=200,
    )


# =============================================================================
# 2. Task Route Handlers (tasks_bp)
# =============================================================================

@tasks_bp.route("/tasks", methods=["GET"])
def list_tasks() -> Tuple[Response, int]:
    """
    Retrieve tasks with optional status and user_id filtering.

    Query parameters:
    - user_id: Filter by owner user ID
    - status: Filter by task status
    """
    user_id: Optional[str] = request.args.get("user_id")
    status: Optional[str] = request.args.get("status")

    try:
        tasks: List[Task] = TaskService.list_tasks(user_id=user_id, status=status)
    except ValidationError as e:
        return error_response(str(e), 400)

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
    Create a new task record with type validation.

    Delegation:
    - Task creation via TaskService.create_task(...)
    """
    data: Dict[str, Any] = get_request_data()
    title: Any = data.get("title") or data.get("name")

    if not title or not str(title).strip():
        return error_response("Task title is required.", 400)

    description: str = str(data.get("description", ""))
    status: str = str(data.get("status", "pending"))
    user_id: Optional[Union[str, int]] = data.get("user_id")

    try:
        task: Task = TaskService.create_task(
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
    except Exception as e:  # pragma: no cover
        return error_response(f"Failed to create task: {str(e)}", 500)


@tasks_bp.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id: str) -> Tuple[Response, int]:
    """Retrieve a single task by ID."""
    task: Optional[Task] = TaskService.get_task_by_id(task_id)
    if task is None:
        return error_response(f"Task '{task_id}' not found.", 404)

    return json_response(
        {"task": task.to_dict()},
        status_code=200,
    )


@tasks_bp.route("/tasks/<task_id>", methods=["PUT", "PATCH"])
def update_task(task_id: str) -> Tuple[Response, int]:
    """Update an existing task by ID."""
    data: Dict[str, Any] = get_request_data()
    if not data:
        return error_response("No update fields provided.", 400)

    try:
        task: Optional[Task] = TaskService.update_task(task_id, **data)
        if task is None:
            return error_response(f"Task '{task_id}' not found.", 404)

        return json_response(
            {"task": task.to_dict()},
            status_code=200,
            message="Task updated successfully.",
        )
    except ValidationError as e:
        return error_response(str(e), 400)
    except Exception as e:  # pragma: no cover
        return error_response(f"An unexpected error occurred: {str(e)}", 500)


@tasks_bp.route("/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id: str) -> Tuple[Response, int]:
    """Delete a task by ID."""
    deleted: bool = TaskService.delete_task(task_id)
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
    app.register_blueprint(auth_bp, url_prefix="")
    app.register_blueprint(auth_bp, url_prefix="/auth", name="auth_prefixed")
    app.register_blueprint(tasks_bp, url_prefix="")
    app.register_blueprint(tasks_bp, url_prefix="/api", name="tasks_prefixed")
