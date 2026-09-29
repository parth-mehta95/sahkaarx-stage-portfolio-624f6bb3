"""
Flask application for Task Manager using Task and User classes with encapsulation.
All routes utilize class methods and model methods instead of direct dictionary operations.
"""

import os
import sys

# Ensure local module directory is prioritized in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from flask import Flask, jsonify, request
from models import Task, User

app = Flask(__name__)


# ---------------------------------------------------------
# Index / Health Check Route
# ---------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """API root providing system status and available endpoints."""
    return jsonify({
        "status": "online",
        "message": "Task Manager API with Encapsulated Task & User Classes",
        "endpoints": {
            "users": "/users",
            "user_detail": "/users/<user_id>",
            "user_tasks": "/users/<user_id>/tasks",
            "user_task_detail": "/users/<user_id>/tasks/<task_id>",
            "tasks": "/tasks",
            "task_detail": "/tasks/<task_id>"
        }
    }), 200


# ---------------------------------------------------------
# User Routes (Using User Class Methods)
# ---------------------------------------------------------

@app.route("/users", methods=["POST"])
def create_user():
    """Create a new user using User.create class method."""
    data = request.get_json() or {}
    name = data.get("name") or data.get("username")
    email = data.get("email", "")
    password = data.get("password", "")
    user_id = data.get("id")

    if not name:
        return jsonify({"error": "User name or username is required"}), 400

    user = User.create(
        name=name,
        email=email,
        password=password,
        user_id=user_id
    )
    return jsonify({
        "message": "User created successfully",
        "user": user.to_dict(include_tasks=True)
    }), 201


@app.route("/users", methods=["GET"])
def list_users():
    """Retrieve all users using User.get_all class method."""
    users = User.get_all()
    return jsonify({
        "users": [user.to_dict() for user in users],
        "count": len(users)
    }), 200


@app.route("/users/<user_id>", methods=["GET"])
def get_user(user_id):
    """Retrieve user details by ID using User.get_by_id class method."""
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user": user.to_dict(include_tasks=True)
    }), 200


# ---------------------------------------------------------
# User-Scoped Task Routes (Using User and Task Methods)
# ---------------------------------------------------------

@app.route("/users/<user_id>/tasks", methods=["POST"])
def create_user_task(user_id):
    """
    Create a new task for a specific user using class & instance methods
    instead of direct dictionary operations.
    """
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    name = data.get("name") or data.get("title")
    description = data.get("description", "")
    status = data.get("status", "pending")
    completed = data.get("completed", False)
    task_id = data.get("id")

    if not name:
        return jsonify({"error": "Task name or title is required"}), 400

    # Create task using User class method / instance method
    task = user.create_task(
        name=name,
        description=description,
        status=status,
        completed=completed,
        task_id=task_id
    )

    return jsonify({
        "message": "Task created successfully",
        "task": task.to_dict()
    }), 201


@app.route("/users/<user_id>/tasks", methods=["GET"])
def get_user_tasks(user_id):
    """
    Retrieve all tasks for a specific user using User class retrieval methods.
    """
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    tasks = user.get_all_tasks()
    return jsonify({
        "tasks": [task.to_dict() for task in tasks],
        "count": len(tasks),
        "user_id": user.id
    }), 200


@app.route("/users/<user_id>/tasks/<task_id>", methods=["GET"])
def get_user_task(user_id, task_id):
    """
    Retrieve a specific task for a user using User.get_task instance method.
    """
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    task = user.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found for this user"}), 404

    return jsonify({
        "task": task.to_dict()
    }), 200


@app.route("/users/<user_id>/tasks/<task_id>", methods=["PUT", "PATCH"])
def update_user_task(user_id, task_id):
    """
    Update a task for a user using User.update_task method.
    """
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    updated_task = user.update_task(
        task_id=task_id,
        name=data.get("name") or data.get("title"),
        description=data.get("description"),
        status=data.get("status"),
        completed=data.get("completed")
    )

    if not updated_task:
        return jsonify({"error": "Task not found"}), 404

    return jsonify({
        "message": "Task updated successfully",
        "task": updated_task.to_dict()
    }), 200


@app.route("/users/<user_id>/tasks/<task_id>", methods=["DELETE"])
def delete_user_task(user_id, task_id):
    """
    Delete a user task using User.delete_task method.
    """
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    success = user.delete_task(task_id)
    if not success:
        return jsonify({"error": "Task not found"}), 404

    return jsonify({
        "message": "Task deleted successfully"
    }), 200


# ---------------------------------------------------------
# Global Task Routes (Using Task Class Methods)
# ---------------------------------------------------------

@app.route("/tasks", methods=["POST"])
def create_task():
    """
    Create a standalone task using Task.create class method.
    """
    data = request.get_json() or {}
    name = data.get("name") or data.get("title")
    description = data.get("description", "")
    status = data.get("status", "pending")
    completed = data.get("completed", False)
    user_id = data.get("user_id")
    task_id = data.get("id")

    if not name:
        return jsonify({"error": "Task name or title is required"}), 400

    task = Task.create(
        name=name,
        description=description,
        status=status,
        completed=completed,
        user_id=user_id,
        task_id=task_id
    )

    # If associated with a user, also attach to user model
    if user_id:
        user = User.get_by_id(user_id)
        if user:
            user.add_task(task)

    return jsonify({
        "message": "Task created successfully",
        "task": task.to_dict()
    }), 201


@app.route("/tasks", methods=["GET"])
def list_tasks():
    """
    Retrieve all tasks using Task.get_all class method.
    """
    tasks = Task.get_all()
    return jsonify({
        "tasks": [task.to_dict() for task in tasks],
        "count": len(tasks)
    }), 200


@app.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    """
    Retrieve a task by ID using Task.get_by_id class method.
    """
    task = Task.get_by_id(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    return jsonify({
        "task": task.to_dict()
    }), 200


@app.route("/tasks/<task_id>", methods=["PUT", "PATCH"])
def update_task(task_id):
    """
    Update a task by ID using Task.update_by_id class method.
    """
    data = request.get_json() or {}
    updated_task = Task.update_by_id(
        task_id=task_id,
        name=data.get("name") or data.get("title"),
        description=data.get("description"),
        status=data.get("status"),
        completed=data.get("completed"),
        user_id=data.get("user_id")
    )

    if not updated_task:
        return jsonify({"error": "Task not found"}), 404

    return jsonify({
        "message": "Task updated successfully",
        "task": updated_task.to_dict()
    }), 200


@app.route("/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    """
    Delete a task by ID using Task.delete_by_id class method.
    """
    success = Task.delete_by_id(task_id)
    if not success:
        return jsonify({"error": "Task not found"}), 404

    return jsonify({
        "message": "Task deleted successfully"
    }), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
