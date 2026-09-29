"""
routes.py - Flask REST API Endpoints with SQLAlchemy ORM Queries.

Scenario:
Refactor REST endpoints to query the database. Replace in-memory task lists with
SQLAlchemy ORM queries and proper HTTP status codes (200, 201, 404, 400).

Deliverables:
- Refactored CRUD endpoints using SQLAlchemy ORM queries
- HTTP status code responses (200, 201, 404, 400)
- User-Task relationship ORM queries
- Robust JSON payload validation and database persistence

Endpoints:
- POST   /tasks             -> 201 Created, 400 Bad Request
- GET    /tasks             -> 200 OK
- GET    /tasks/<id>        -> 200 OK, 404 Not Found, 400 Bad Request
- PUT    /tasks/<id>        -> 200 OK, 400 Bad Request, 404 Not Found
- DELETE /tasks/<id>        -> 200 OK, 404 Not Found, 400 Bad Request
- POST   /users             -> 201 Created, 400 Bad Request
- GET    /users             -> 200 OK
- GET    /users/<id>        -> 200 OK, 404 Not Found, 400 Bad Request
- GET    /users/<id>/tasks   -> 200 OK, 404 Not Found, 400 Bad Request
- POST   /users/<id>/tasks   -> 201 Created, 404 Not Found, 400 Bad Request
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple, Union
from flask import Blueprint, Flask, Response, jsonify, request
from sqlalchemy.exc import IntegrityError

try:
    from models import Task, User, db
except ImportError:
    from .models import Task, User, db

# Blueprint for task and user REST API endpoints
tasks_bp = Blueprint("tasks_bp", __name__)


# ============================================================================
# Helper Functions
# ============================================================================

def _parse_int_id(val: Any) -> Optional[int]:
    """Safely parse integer ID or return None."""
    try:
        parsed = int(val)
        return parsed if parsed > 0 else None
    except (ValueError, TypeError):
        return None


def _get_json_payload() -> Tuple[Optional[Dict[str, Any]], Optional[Response]]:
    """
    Safely extract and validate JSON body from the incoming request.
    Returns (data, None) on success or (None, error_response) on failure.
    """
    if not request.is_json and request.content_type != "application/json":
        data = request.get_json(silent=True)
        if data is None:
            return None, (jsonify({
                "error": "Bad Request",
                "message": "Content-Type must be application/json and contain valid JSON",
            }), 400)
    else:
        data = request.get_json(silent=True)

    if data is None or not isinstance(data, dict):
        return None, (jsonify({
            "error": "Bad Request",
            "message": "Request payload must be a valid JSON object",
        }), 400)

    return data, None


# ============================================================================
# Task CRUD Endpoints (Using SQLAlchemy ORM Queries)
# ============================================================================

@tasks_bp.route("/tasks", methods=["POST"])
@tasks_bp.route("/api/tasks", methods=["POST"])
def create_task() -> Tuple[Response, int]:
    """
    POST /tasks
    Create a new task and persist it to the SQLite database via SQLAlchemy ORM.

    Status codes:
    - 201 Created: Task successfully created and saved in the database
    - 400 Bad Request: Missing or invalid required fields (e.g. title)
    """
    data, err_resp = _get_json_payload()
    if err_resp:
        return err_resp

    title = data.get("title")
    if title is None or not isinstance(title, str) or not title.strip():
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'title' is required and must be a non-empty string",
        }), 400

    description = data.get("description", "")
    if description is not None and not isinstance(description, str):
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'description' must be a string",
        }), 400

    status = data.get("status", "pending")
    if not isinstance(status, str) or not status.strip():
        status = "pending"
    else:
        status = status.strip()

    completed = data.get("completed", False)
    if not isinstance(completed, bool):
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'completed' must be a boolean",
        }), 400

    user_id = data.get("user_id")
    if user_id is not None:
        parsed_user_id = _parse_int_id(user_id)
        if parsed_user_id is None:
            return jsonify({
                "error": "Bad Request",
                "message": "Field 'user_id' must be a positive integer",
            }), 400
        # ORM Query: verify referenced User exists in database
        user = User.query.get(parsed_user_id)
        if not user:
            return jsonify({
                "error": "Bad Request",
                "message": f"User with id '{parsed_user_id}' does not exist",
            }), 400
        user_id = parsed_user_id

    due_date = data.get("due_date")

    try:
        task = Task(
            title=title,
            description=description,
            due_date=due_date,
            status=status,
            completed=completed,
            user_id=user_id,
        )
        db.session.add(task)
        db.session.commit()
    except ValueError as ve:
        db.session.rollback()
        return jsonify({"error": "Bad Request", "message": str(ve)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": "Bad Request", "message": str(exc)}), 400

    return jsonify({
        "message": "Task created successfully",
        "task": task.to_dict(),
    }), 201


@tasks_bp.route("/tasks", methods=["GET"])
@tasks_bp.route("/api/tasks", methods=["GET"])
def get_tasks() -> Tuple[Response, int]:
    """
    GET /tasks
    Retrieve tasks using SQLAlchemy ORM queries with optional filtering.

    Query parameters supported:
    - ?status=<status>: Filter by task status
    - ?user_id=<user_id>: Filter by associated user
    - ?completed=<true|false>: Filter by completion flag
    - ?q=<search>: Case-insensitive title search

    Status codes:
    - 200 OK: Returns matching tasks list and total count
    """
    query = Task.query

    status_filter = request.args.get("status")
    if status_filter:
        query = query.filter(Task.status == status_filter.strip())

    user_id_param = request.args.get("user_id")
    if user_id_param:
        parsed_uid = _parse_int_id(user_id_param)
        if parsed_uid:
            query = query.filter(Task.user_id == parsed_uid)

    completed_param = request.args.get("completed")
    if completed_param is not None:
        is_completed = completed_param.strip().lower() in ("true", "1", "yes")
        query = query.filter(Task.completed == is_completed)

    search_param = request.args.get("q")
    if search_param:
        query = query.filter(Task.title.ilike(f"%{search_param.strip()}%"))

    # Execute ORM query
    tasks = query.order_by(Task.id.asc()).all()

    return jsonify({
        "count": len(tasks),
        "tasks": [t.to_dict() for t in tasks],
    }), 200


@tasks_bp.route("/tasks/<task_id>", methods=["GET"])
@tasks_bp.route("/api/tasks/<task_id>", methods=["GET"])
def get_task(task_id: str) -> Tuple[Response, int]:
    """
    GET /tasks/<id>
    Retrieve a single task by ID using SQLAlchemy ORM query.

    Status codes:
    - 200 OK: Task found and returned
    - 404 Not Found: Task ID does not exist in database
    - 400 Bad Request: Invalid non-numeric task ID
    """
    parsed_id = _parse_int_id(task_id)
    if parsed_id is None:
        return jsonify({
            "error": "Bad Request",
            "message": f"Invalid task ID '{task_id}'. Must be a positive integer.",
        }), 400

    # ORM Query: Query by primary key
    task = Task.query.get(parsed_id)
    if not task:
        return jsonify({
            "error": "Not Found",
            "message": f"Task with id '{task_id}' not found",
        }), 404

    return jsonify(task.to_dict()), 200


@tasks_bp.route("/tasks/<task_id>", methods=["PUT"])
@tasks_bp.route("/api/tasks/<task_id>", methods=["PUT"])
def update_task(task_id: str) -> Tuple[Response, int]:
    """
    PUT /tasks/<id>
    Update an existing task in the database via SQLAlchemy ORM.

    Status codes:
    - 200 OK: Task successfully updated and committed to database
    - 400 Bad Request: Invalid payload or validation failure
    - 404 Not Found: Task ID does not exist in database
    """
    parsed_id = _parse_int_id(task_id)
    if parsed_id is None:
        return jsonify({
            "error": "Bad Request",
            "message": f"Invalid task ID '{task_id}'. Must be a positive integer.",
        }), 400

    # ORM Query: Check if task exists
    task = Task.query.get(parsed_id)
    if not task:
        return jsonify({
            "error": "Not Found",
            "message": f"Task with id '{task_id}' not found",
        }), 404

    data, err_resp = _get_json_payload()
    if err_resp:
        return err_resp

    if "title" in data:
        title = data["title"]
        if title is None or not isinstance(title, str) or not title.strip():
            return jsonify({
                "error": "Bad Request",
                "message": "Field 'title' cannot be empty",
            }), 400

    if "user_id" in data:
        new_uid = data["user_id"]
        if new_uid is not None:
            parsed_uid = _parse_int_id(new_uid)
            if parsed_uid is None:
                return jsonify({
                    "error": "Bad Request",
                    "message": "Field 'user_id' must be a positive integer",
                }), 400
            # ORM Query: Verify foreign key existence
            user = User.query.get(parsed_uid)
            if not user:
                return jsonify({
                    "error": "Bad Request",
                    "message": f"User with id '{parsed_uid}' does not exist",
                }), 400

    try:
        task.update(
            title=data.get("title"),
            description=data.get("description"),
            due_date=data.get("due_date"),
            status=data.get("status"),
            completed=data.get("completed"),
            user_id=data.get("user_id"),
        )
        db.session.commit()
    except ValueError as ve:
        db.session.rollback()
        return jsonify({"error": "Bad Request", "message": str(ve)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": "Bad Request", "message": str(exc)}), 400

    return jsonify({
        "message": "Task updated successfully",
        "task": task.to_dict(),
    }), 200


@tasks_bp.route("/tasks/<task_id>", methods=["DELETE"])
@tasks_bp.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id: str) -> Tuple[Response, int]:
    """
    DELETE /tasks/<id>
    Delete a task from the database via SQLAlchemy ORM.

    Status codes:
    - 200 OK: Task successfully deleted from the database
    - 404 Not Found: Task ID does not exist in database
    - 400 Bad Request: Invalid non-numeric task ID
    """
    parsed_id = _parse_int_id(task_id)
    if parsed_id is None:
        return jsonify({
            "error": "Bad Request",
            "message": f"Invalid task ID '{task_id}'. Must be a positive integer.",
        }), 400

    # ORM Query: Retrieve task
    task = Task.query.get(parsed_id)
    if not task:
        return jsonify({
            "error": "Not Found",
            "message": f"Task with id '{task_id}' not found",
        }), 404

    db.session.delete(task)
    db.session.commit()

    return jsonify({
        "message": f"Task '{task_id}' deleted successfully",
    }), 200


# ============================================================================
# User & Relationship ORM Endpoints
# ============================================================================

@tasks_bp.route("/users", methods=["POST"])
@tasks_bp.route("/api/users", methods=["POST"])
def create_user() -> Tuple[Response, int]:
    """
    POST /users
    Create a new user in the database.

    Status codes:
    - 201 Created: User created successfully
    - 400 Bad Request: Missing username/email or duplicate constraint error
    """
    data, err_resp = _get_json_payload()
    if err_resp:
        return err_resp

    username = data.get("username")
    email = data.get("email")
    password = data.get("password", "secret123")

    if not username or not isinstance(username, str) or not username.strip():
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'username' is required and must be non-empty",
        }), 400

    if not email or not isinstance(email, str) or "@" not in email:
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'email' is required and must be a valid email",
        }), 400

    try:
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "Bad Request",
            "message": "Username or email already exists",
        }), 400
    except ValueError as ve:
        db.session.rollback()
        return jsonify({"error": "Bad Request", "message": str(ve)}), 400

    return jsonify({
        "message": "User created successfully",
        "user": user.to_dict(),
    }), 201


@tasks_bp.route("/users", methods=["GET"])
@tasks_bp.route("/api/users", methods=["GET"])
def get_users() -> Tuple[Response, int]:
    """
    GET /users
    List all users using ORM query.

    Status codes:
    - 200 OK: Returns all users
    """
    users = User.query.order_by(User.id.asc()).all()
    return jsonify({
        "count": len(users),
        "users": [u.to_dict() for u in users],
    }), 200


@tasks_bp.route("/users/<user_id>", methods=["GET"])
@tasks_bp.route("/api/users/<user_id>", methods=["GET"])
def get_user(user_id: str) -> Tuple[Response, int]:
    """
    GET /users/<id>
    Retrieve single user details using ORM query.

    Status codes:
    - 200 OK: User found
    - 404 Not Found: User does not exist
    - 400 Bad Request: Invalid user ID
    """
    parsed_id = _parse_int_id(user_id)
    if parsed_id is None:
        return jsonify({
            "error": "Bad Request",
            "message": f"Invalid user ID '{user_id}'",
        }), 400

    user = User.query.get(parsed_id)
    if not user:
        return jsonify({
            "error": "Not Found",
            "message": f"User with id '{user_id}' not found",
        }), 404

    return jsonify(user.to_dict()), 200


@tasks_bp.route("/users/<user_id>/tasks", methods=["GET"])
@tasks_bp.route("/api/users/<user_id>/tasks", methods=["GET"])
def get_user_tasks(user_id: str) -> Tuple[Response, int]:
    """
    GET /users/<id>/tasks
    Query all tasks assigned to a specific user via SQLAlchemy ORM relationship.

    Status codes:
    - 200 OK: Tasks retrieved via ORM relationship
    - 404 Not Found: User does not exist
    - 400 Bad Request: Invalid user ID
    """
    parsed_id = _parse_int_id(user_id)
    if parsed_id is None:
        return jsonify({
            "error": "Bad Request",
            "message": f"Invalid user ID '{user_id}'",
        }), 400

    # ORM Query: Find user and traverse relationship
    user = User.query.get(parsed_id)
    if not user:
        return jsonify({
            "error": "Not Found",
            "message": f"User with id '{user_id}' not found",
        }), 404

    tasks = user.tasks  # Evaluated via ORM relationship
    return jsonify({
        "user_id": user.id,
        "username": user.username,
        "count": len(tasks),
        "tasks": [t.to_dict() for t in tasks],
    }), 200


@tasks_bp.route("/users/<user_id>/tasks", methods=["POST"])
@tasks_bp.route("/api/users/<user_id>/tasks", methods=["POST"])
def create_user_task(user_id: str) -> Tuple[Response, int]:
    """
    POST /users/<id>/tasks
    Create a task linked directly to a specific user via ORM relationship.

    Status codes:
    - 201 Created: Task created and associated with user
    - 404 Not Found: User does not exist
    - 400 Bad Request: Invalid payload or user ID
    """
    parsed_id = _parse_int_id(user_id)
    if parsed_id is None:
        return jsonify({
            "error": "Bad Request",
            "message": f"Invalid user ID '{user_id}'",
        }), 400

    user = User.query.get(parsed_id)
    if not user:
        return jsonify({
            "error": "Not Found",
            "message": f"User with id '{user_id}' not found",
        }), 404

    data, err_resp = _get_json_payload()
    if err_resp:
        return err_resp

    title = data.get("title")
    if not title or not isinstance(title, str) or not title.strip():
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'title' is required and must be non-empty",
        }), 400

    try:
        task = Task(
            title=title,
            description=data.get("description", ""),
            due_date=data.get("due_date"),
            status=data.get("status", "pending"),
            completed=data.get("completed", False),
            user_id=user.id,
        )
        db.session.add(task)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": "Bad Request", "message": str(exc)}), 400

    return jsonify({
        "message": "Task created successfully for user",
        "task": task.to_dict(),
    }), 201


# ============================================================================
# Application Factory
# ============================================================================

def create_app(database_uri: Optional[str] = None) -> Flask:
    """
    Create and configure the Flask application with SQLAlchemy ORM.

    Args:
        database_uri: Optional database connection URI (defaults to SQLite task_manager.db).
    """
    app = Flask(__name__)

    if database_uri is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "task_manager.db")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_uri

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JSON_SORT_KEYS"] = False

    # Initialize SQLAlchemy extension
    db.init_app(app)

    # Register Blueprint
    app.register_blueprint(tasks_bp)

    # Error Handlers for consistent JSON responses and status codes
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad Request", "message": getattr(error, "description", "Bad Request")}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not Found", "message": "The requested resource was not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method Not Allowed", "message": "Method not allowed for this endpoint"}), 405

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}), 500

    # Ensure tables are created
    with app.app_context():
        db.create_all()

    return app


# Default application instance
app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
