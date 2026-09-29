"""
routes.py - Flask REST API Endpoints for Task CRUD Operations.

Scenario:
Your team needs REST endpoints for task operations. Build CRUD endpoints using proper
HTTP methods and status codes.

Deliverables:
- Flask CRUD endpoints (POST /tasks, GET /tasks, GET /tasks/<id>, PUT /tasks/<id>, DELETE /tasks/<id>)
- HTTP status code handling (201, 200, 400, 404, 405, 500)
- Endpoints accept and return valid JSON

Usage:
    from routes import app, tasks_bp
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from flask import Blueprint, Flask, Response, jsonify, make_response, request

# Create Blueprint for Task CRUD routes
tasks_bp = Blueprint("tasks", __name__)

# In-memory storage for tasks
_tasks_db: Dict[int, Dict[str, Any]] = {}
_id_counter: int = 0


# ============================================================================
# Task Database Helper Functions
# ============================================================================

def reset_db() -> None:
    """Clear in-memory database and reset ID counter (used for testing)."""
    global _tasks_db, _id_counter
    _tasks_db.clear()
    _id_counter = 0


def get_all_tasks() -> List[Dict[str, Any]]:
    """Retrieve all stored tasks as a list of dictionaries."""
    return list(_tasks_db.values())


def find_task_by_id(task_id: Union[int, str]) -> Optional[Dict[str, Any]]:
    """
    Look up a task by ID supporting both integer and string representations.

    Args:
        task_id: The integer or string task identifier.

    Returns:
        The task dictionary if found, or None.
    """
    try:
        numeric_id = int(task_id)
        if numeric_id in _tasks_db:
            return _tasks_db[numeric_id]
    except (ValueError, TypeError):
        pass

    # Fallback search if stored with string key
    for t_id, task in _tasks_db.items():
        if str(t_id) == str(task_id) or str(task.get("id")) == str(task_id):
            return task
    return None


def add_task(
    title: str,
    description: str = "",
    status: str = "pending",
    task_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Create and store a new task record.

    Args:
        title: Title of the task (required).
        description: Detailed task description.
        status: Task status ('pending', 'in_progress', 'completed').
        task_id: Optional explicit ID.

    Returns:
        The newly created task dictionary.
    """
    global _id_counter
    if task_id is not None:
        new_id = int(task_id)
        if new_id > _id_counter:
            _id_counter = new_id
    else:
        _id_counter += 1
        new_id = _id_counter

    now_iso = datetime.now(timezone.utc).isoformat()
    new_task = {
        "id": new_id,
        "title": title.strip(),
        "description": description.strip() if description else "",
        "status": status.strip() if status else "pending",
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    _tasks_db[new_id] = new_task
    return new_task


def update_task_record(
    task_id: Union[int, str],
    updates: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Update fields of an existing task record.

    Args:
        task_id: ID of the task to update.
        updates: Dictionary of fields to update.

    Returns:
        The updated task dictionary or None if task doesn't exist.
    """
    task = find_task_by_id(task_id)
    if task is None:
        return None

    if "title" in updates and updates["title"] is not None:
        task["title"] = str(updates["title"]).strip()

    if "description" in updates and updates["description"] is not None:
        task["description"] = str(updates["description"]).strip()

    if "status" in updates and updates["status"] is not None:
        task["status"] = str(updates["status"]).strip()

    task["updated_at"] = datetime.now(timezone.utc).isoformat()
    return task


def delete_task_record(task_id: Union[int, str]) -> bool:
    """
    Delete a task by ID.

    Args:
        task_id: ID of task to delete.

    Returns:
        True if deleted, False if task was not found.
    """
    task = find_task_by_id(task_id)
    if task is None:
        return False

    real_id = task["id"]
    if real_id in _tasks_db:
        del _tasks_db[real_id]
        return True
    return False


# ============================================================================
# REST API Endpoints (CRUD)
# ============================================================================

@tasks_bp.route("/tasks", methods=["POST"])
def create_task() -> Tuple[Response, int]:
    """
    POST /tasks
    Create a new task.

    Requirements:
    - HTTP Status Code: 201 Created on success
    - HTTP Status Code: 400 Bad Request on missing/invalid JSON or title
    - Content-Type: application/json
    """
    # Verify JSON content
    if not request.is_json and request.content_type != "application/json":
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({
                "error": "Bad Request",
                "message": "Request must contain valid application/json body"
            }), 400
    else:
        data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Bad Request",
            "message": "JSON body must be an object/dictionary"
        }), 400

    title = data.get("title")
    if title is None or not isinstance(title, str) or not title.strip():
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'title' is required and must be a non-empty string"
        }), 400

    description = data.get("description", "")
    status = data.get("status", "pending")

    # Optional status validation
    valid_statuses = {"pending", "in_progress", "completed", "done", "cancelled"}
    if status and str(status).lower() not in valid_statuses:
        status = "pending"

    task = add_task(title=title, description=description, status=status)

    return jsonify({
        "message": "Task created successfully",
        "task": task
    }), 201


@tasks_bp.route("/tasks", methods=["GET"])
def get_tasks() -> Tuple[Response, int]:
    """
    GET /tasks
    Retrieve all tasks.

    Requirements:
    - HTTP Status Code: 200 OK
    - Accepts optional query param: ?status=pending
    - Returns valid JSON array of tasks
    """
    status_filter = request.args.get("status")
    tasks = get_all_tasks()

    if status_filter:
        tasks = [t for t in tasks if t.get("status") == status_filter]

    return jsonify({
        "count": len(tasks),
        "tasks": tasks
    }), 200


@tasks_bp.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id: str) -> Tuple[Response, int]:
    """
    GET /tasks/<id>
    Retrieve a single task by ID.

    Requirements:
    - HTTP Status Code: 200 OK on success
    - HTTP Status Code: 404 Not Found if task does not exist
    - Returns valid JSON
    """
    task = find_task_by_id(task_id)
    if task is None:
        return jsonify({
            "error": "Not Found",
            "message": f"Task with id '{task_id}' not found"
        }), 404

    return jsonify(task), 200


@tasks_bp.route("/tasks/<task_id>", methods=["PUT"])
def update_task(task_id: str) -> Tuple[Response, int]:
    """
    PUT /tasks/<id>
    Update an existing task by ID.

    Requirements:
    - HTTP Status Code: 200 OK on success
    - HTTP Status Code: 400 Bad Request on invalid JSON or bad field values
    - HTTP Status Code: 404 Not Found if task does not exist
    - Returns valid JSON with updated task
    """
    task = find_task_by_id(task_id)
    if task is None:
        return jsonify({
            "error": "Not Found",
            "message": f"Task with id '{task_id}' not found"
        }), 404

    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({
            "error": "Bad Request",
            "message": "Request body must contain valid JSON object"
        }), 400

    if "title" in data:
        title = data["title"]
        if title is None or not isinstance(title, str) or not title.strip():
            return jsonify({
                "error": "Bad Request",
                "message": "Field 'title' cannot be empty"
            }), 400

    updated = update_task_record(task_id, data)
    return jsonify({
        "message": "Task updated successfully",
        "task": updated
    }), 200


@tasks_bp.route("/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id: str) -> Tuple[Response, int]:
    """
    DELETE /tasks/<id>
    Delete an existing task by ID.

    Requirements:
    - HTTP Status Code: 200 OK on success (or 204)
    - HTTP Status Code: 404 Not Found if task does not exist
    - Returns valid JSON confirmation
    """
    success = delete_task_record(task_id)
    if not success:
        return jsonify({
            "error": "Not Found",
            "message": f"Task with id '{task_id}' not found"
        }), 404

    return jsonify({
        "message": f"Task {task_id} deleted successfully",
        "id": task_id
    }), 200


# ============================================================================
# Flask Application Factory
# ============================================================================

def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """
    Create and configure the Flask application.

    Registers:
    - Task CRUD blueprint
    - Root status route
    - Global JSON error handlers (400, 404, 405, 500)
    """
    flask_app = Flask(__name__)
    flask_app.config["JSON_SORT_KEYS"] = False

    if test_config:
        flask_app.config.update(test_config)

    # Register blueprint
    flask_app.register_blueprint(tasks_bp)

    # Root route for API discovery
    @flask_app.route("/", methods=["GET"])
    def index():
        return jsonify({
            "service": "Task Manager REST API",
            "version": "1.0.0",
            "status": "healthy",
            "endpoints": {
                "create_task": "POST /tasks",
                "list_tasks": "GET /tasks",
                "get_task": "GET /tasks/<id>",
                "update_task": "PUT /tasks/<id>",
                "delete_task": "DELETE /tasks/<id>"
            }
        }), 200

    # Custom JSON error handlers
    @flask_app.errorhandler(400)
    def handle_bad_request(error):
        return jsonify({
            "error": "Bad Request",
            "message": getattr(error, "description", "The request was invalid or could not be processed.")
        }), 400

    @flask_app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            "error": "Not Found",
            "message": getattr(error, "description", "The requested resource was not found on this server.")
        }), 404

    @flask_app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({
            "error": "Method Not Allowed",
            "message": "The HTTP method used is not allowed for this endpoint."
        }), 405

    @flask_app.errorhandler(500)
    def handle_internal_error(error):
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected server error occurred."
        }), 500

    return flask_app


# Expose default application instance for direct WSGI or import usage
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
