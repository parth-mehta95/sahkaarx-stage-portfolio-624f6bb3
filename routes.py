"""routes.py - Flask API routes with request validation and complete type hints."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from flask import Blueprint, jsonify, request, Response
from models import db, Task, User

api_bp: Blueprint = Blueprint("api", __name__)


def parse_date_string(date_str: Optional[str]) -> Tuple[bool, Optional[date], Optional[str]]:
    """Validate and parse a date string in YYYY-MM-DD format.

    Args:
        date_str: The string representation of the date, or None.

    Returns:
        A tuple of (is_valid, parsed_date, error_message).
    """
    if date_str is None or (isinstance(date_str, str) and not date_str.strip()):
        return True, None, None

    if not isinstance(date_str, str):
        return False, None, "Due date must be a string in YYYY-MM-DD format."

    clean_str: str = date_str.strip()
    try:
        parsed: date = datetime.strptime(clean_str, "%Y-%m-%d").date()
        return True, parsed, None
    except ValueError:
        return False, None, f"Invalid date format or value for '{clean_str}'. Expected YYYY-MM-DD."


def validate_task_input(
    data: Optional[Dict[str, Any]],
    is_update: bool = False,
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Validate user input for creating or updating a task before database operations.

    Args:
        data: The JSON payload from the request.
        is_update: Whether the validation is for an update (PUT) or creation (POST).

    Returns:
        A tuple of (is_valid, error_message, sanitized_data).
    """
    if data is None or not isinstance(data, dict):
        return False, "Request body must be a valid JSON object.", None

    sanitized: Dict[str, Any] = {}

    # Validate Title
    if not is_update:
        if "title" not in data:
            return False, "Title is required.", None
        title: Any = data.get("title")
        if not isinstance(title, str) or not title.strip():
            return False, "Title cannot be empty.", None
        sanitized["title"] = title.strip()
    else:
        if "title" in data:
            title = data.get("title")
            if not isinstance(title, str) or not title.strip():
                return False, "Title cannot be empty.", None
            sanitized["title"] = title.strip()

    # Validate Description
    if "description" in data:
        desc: Any = data.get("description")
        if desc is not None and not isinstance(desc, str):
            return False, "Description must be a string.", None
        sanitized["description"] = desc.strip() if desc else ""

    # Validate Due Date
    if "due_date" in data:
        raw_due_date: Any = data.get("due_date")
        if raw_due_date is not None:
            if not isinstance(raw_due_date, str):
                return False, "Due date must be a string in YYYY-MM-DD format.", None
            is_valid_date, parsed_date, date_err = parse_date_string(raw_due_date)
            if not is_valid_date:
                return False, date_err, None
            sanitized["due_date"] = parsed_date
        else:
            sanitized["due_date"] = None

    # Validate Status
    if "status" in data:
        status: Any = data.get("status")
        if status is not None:
            if not isinstance(status, str) or not status.strip():
                return False, "Status must be a non-empty string.", None
            sanitized["status"] = status.strip()

    # Validate Completed flag
    if "completed" in data:
        completed: Any = data.get("completed")
        if completed is not None:
            if not isinstance(completed, bool):
                return False, "Completed field must be a boolean.", None
            sanitized["completed"] = completed

    # Validate User ID
    if "user_id" in data:
        user_id: Any = data.get("user_id")
        if user_id is not None:
            if not isinstance(user_id, int) or user_id <= 0:
                return False, "User ID must be a positive integer.", None
            user: Optional[User] = db.session.get(User, user_id)
            if not user:
                return False, f"User with ID {user_id} does not exist.", None
            sanitized["user_id"] = user_id
        else:
            sanitized["user_id"] = None

    return True, None, sanitized


# ==========================================================
# Task Routes
# ==========================================================


@api_bp.route("/tasks", methods=["POST"])
def create_task() -> Tuple[Response, int]:
    """Create a new task with strict input validation."""
    data: Optional[Dict[str, Any]] = request.get_json(silent=True)
    is_valid, error_msg, validated_data = validate_task_input(data, is_update=False)

    if not is_valid or validated_data is None:
        return jsonify({"error": error_msg}), 400

    try:
        new_task: Task = Task(
            title=validated_data["title"],
            description=validated_data.get("description", ""),
            due_date=validated_data.get("due_date"),
            status=validated_data.get("status", "pending"),
            completed=validated_data.get("completed", False),
            user_id=validated_data.get("user_id"),
        )
        db.session.add(new_task)
        db.session.commit()
        return jsonify(new_task.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@api_bp.route("/tasks", methods=["GET"])
def get_tasks() -> Tuple[Response, int]:
    """Retrieve all tasks."""
    tasks: List[Task] = Task.query.all()
    task_list: List[Dict[str, Any]] = [task.to_dict() for task in tasks]
    return jsonify(task_list), 200


@api_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id: int) -> Tuple[Response, int]:
    """Retrieve a single task by ID."""
    task: Optional[Task] = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": f"Task with ID {task_id} not found."}), 404
    return jsonify(task.to_dict()), 200


@api_bp.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id: int) -> Tuple[Response, int]:
    """Update an existing task with input validation."""
    task: Optional[Task] = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": f"Task with ID {task_id} not found."}), 404

    data: Optional[Dict[str, Any]] = request.get_json(silent=True)
    is_valid, error_msg, validated_data = validate_task_input(data, is_update=True)

    if not is_valid or validated_data is None:
        return jsonify({"error": error_msg}), 400

    try:
        task.update(
            title=validated_data.get("title"),
            description=validated_data.get("description"),
            due_date=validated_data.get("due_date"),
            status=validated_data.get("status"),
            completed=validated_data.get("completed"),
        )
        if "user_id" in validated_data:
            task.user_id = validated_data["user_id"]

        db.session.commit()
        return jsonify(task.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@api_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id: int) -> Tuple[Response, int]:
    """Delete a task by ID."""
    task: Optional[Task] = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": f"Task with ID {task_id} not found."}), 404

    try:
        db.session.delete(task)
        db.session.commit()
        return jsonify({"message": f"Task {task_id} deleted successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500


# ==========================================================
# User & Auth Routes
# ==========================================================


@api_bp.route("/register", methods=["POST"])
def register() -> Tuple[Response, int]:
    """Register a new user with input validation."""
    data: Optional[Dict[str, Any]] = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Request body must be a valid JSON object."}), 400

    username: Optional[str] = data.get("username")
    email: Optional[str] = data.get("email")
    password: Optional[str] = data.get("password")

    if not username or not isinstance(username, str) or not username.strip():
        return jsonify({"error": "Username is required and cannot be empty."}), 400
    if not email or not isinstance(email, str) or not email.strip():
        return jsonify({"error": "Email is required and cannot be empty."}), 400
    if not password or not isinstance(password, str) or not password.strip():
        return jsonify({"error": "Password is required and cannot be empty."}), 400

    username = username.strip()
    email = email.strip()

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered."}), 400

    try:
        user: User = User.register(username=username, email=email, password=password)
        return jsonify(user.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@api_bp.route("/login", methods=["POST"])
def login() -> Tuple[Response, int]:
    """Authenticate a user."""
    data: Optional[Dict[str, Any]] = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Request body must be a valid JSON object."}), 400

    username: Optional[str] = data.get("username")
    password: Optional[str] = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    user: Optional[User] = User.authenticate(username=username.strip(), password=password)
    if not user:
        return jsonify({"error": "Invalid username or password."}), 401

    return jsonify({"message": "Login successful.", "user": user.to_dict()}), 200


@api_bp.route("/users/<int:user_id>/tasks", methods=["GET"])
def get_user_tasks(user_id: int) -> Tuple[Response, int]:
    """Retrieve all tasks for a specific user."""
    user: Optional[User] = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": f"User with ID {user_id} not found."}), 404

    tasks: List[Task] = user.get_tasks()
    task_list: List[Dict[str, Any]] = [task.to_dict() for task in tasks]
    return jsonify(task_list), 200
