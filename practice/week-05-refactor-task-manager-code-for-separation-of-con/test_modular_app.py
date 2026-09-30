"""
test_modular_app.py - Comprehensive Unit & Integration Tests for Separation of Concerns.

Verifies:
1. Separation of concerns:
   - models.py contains User, Task, and custom exceptions.
   - routes.py contains auth_bp, tasks_bp, and route handlers.
   - utils.py contains hashing, validation, and request/response helpers.
   - app.py coordinates models, routes, and utils into a configured Flask app.
2. Endpoint functional testing:
   - User registration (201, 400, 409)
   - User authentication / login (200, 400, 401)
   - User retrieval (200, 404)
   - Task CRUD endpoints (GET, POST, PUT, DELETE)
   - Query filtering by status and user_id
"""

from __future__ import annotations

import unittest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from models import Task, User, ValidationError, UserAlreadyExistsError
from routes import auth_bp, tasks_bp
from utils import (
    hash_password,
    validate_email_format,
    validate_password_strength,
    validate_task_status,
    validate_username,
    verify_password,
)


class TestSeparationOfConcernsArchitecture(unittest.TestCase):
    """Verify architectural boundaries and separation of concerns."""

    def test_models_exports(self) -> None:
        """Verify models.py exports domain classes and domain exceptions."""
        self.assertTrue(hasattr(User, "register"))
        self.assertTrue(hasattr(User, "authenticate"))
        self.assertTrue(hasattr(Task, "create"))
        self.assertTrue(hasattr(Task, "get_by_id"))

    def test_routes_exports(self) -> None:
        """Verify routes.py exports blueprints and route registration helper."""
        self.assertEqual(auth_bp.name, "auth")
        self.assertEqual(tasks_bp.name, "tasks")

    def test_utils_exports(self) -> None:
        """Verify utils.py exports helper functions."""
        pwd = "SecretPassword123!"
        hashed = hash_password(pwd)
        self.assertNotEqual(pwd, hashed)
        self.assertTrue(verify_password(pwd, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

        # Test validations
        self.assertEqual(validate_username("alice_99"), "alice_99")
        with self.assertRaises(ValidationError):
            validate_username("ab")

        self.assertEqual(validate_password_strength("securepass"), "securepass")
        with self.assertRaises(ValidationError):
            validate_password_strength("123")

        self.assertEqual(validate_email_format("user@example.com"), "user@example.com")
        with self.assertRaises(ValidationError):
            validate_email_format("invalid-email")

        self.assertEqual(validate_task_status("in_progress"), "in_progress")
        self.assertEqual(validate_task_status("done"), "completed")
        with self.assertRaises(ValidationError):
            validate_task_status("bogus_status")


class TestFlaskEndpoints(unittest.TestCase):
    """Integration tests for all Flask API endpoints."""

    def setUp(self) -> None:
        """Reset state and instantiate test client."""
        User.clear_all()
        Task.clear_all()
        self.app: Flask = create_app({"TESTING": True})
        self.client: FlaskClient = self.app.test_client()

    def tearDown(self) -> None:
        """Clean up repositories."""
        User.clear_all()
        Task.clear_all()

    # -------------------------------------------------------------------------
    # Discovery / Health Check
    # -------------------------------------------------------------------------

    def test_index_discovery(self) -> None:
        """GET / returns system status and endpoint discovery."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertIn("service", json_data)
        self.assertEqual(json_data["status_code"], 200)

    # -------------------------------------------------------------------------
    # Authentication Endpoints
    # -------------------------------------------------------------------------

    def test_register_success(self) -> None:
        """POST /register creates a new user and returns 201."""
        res = self.client.post(
            "/register",
            json={
                "username": "charlie",
                "password": "Password123",
                "email": "charlie@example.com",
            },
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["user"]["username"], "charlie")
        self.assertEqual(data["user"]["email"], "charlie@example.com")
        # Ensure password_hash is NEVER leaked
        self.assertNotIn("password_hash", data["user"])

    def test_register_duplicate_username(self) -> None:
        """POST /register returns 409 Conflict if username already exists."""
        self.client.post("/register", json={"username": "dave", "password": "Password123"})
        res = self.client.post("/register", json={"username": "dave", "password": "Password123"})
        self.assertEqual(res.status_code, 409)
        self.assertIn("already registered", res.get_json()["error"])

    def test_register_missing_fields(self) -> None:
        """POST /register returns 400 Bad Request if fields are missing or invalid."""
        res1 = self.client.post("/register", json={"password": "Password123"})
        self.assertEqual(res1.status_code, 400)

        res2 = self.client.post("/register", json={"username": "dave"})
        self.assertEqual(res2.status_code, 400)

        res3 = self.client.post("/register", json={"username": "ab", "password": "123"})
        self.assertEqual(res3.status_code, 400)

    def test_login_success(self) -> None:
        """POST /login returns 200 and user data with valid credentials."""
        self.client.post("/register", json={"username": "eve", "password": "MySecretPassword"})
        res = self.client.post("/login", json={"username": "eve", "password": "MySecretPassword"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["user"]["username"], "eve")
        self.assertEqual(data["message"], "Login successful.")

    def test_login_invalid_password(self) -> None:
        """POST /login returns 401 Unauthorized for incorrect password."""
        self.client.post("/register", json={"username": "frank", "password": "CorrectPassword"})
        res = self.client.post("/login", json={"username": "frank", "password": "WrongPassword"})
        self.assertEqual(res.status_code, 401)
        self.assertIn("Invalid username or password", res.get_json()["error"])

    def test_login_nonexistent_user(self) -> None:
        """POST /login returns 401 Unauthorized for nonexistent user."""
        res = self.client.post("/login", json={"username": "ghost", "password": "Password123"})
        self.assertEqual(res.status_code, 401)

    def test_logout(self) -> None:
        """POST /logout returns 200 OK."""
        res = self.client.post("/logout")
        self.assertEqual(res.status_code, 200)

    def test_get_users_and_by_username(self) -> None:
        """GET /users and GET /users/<username> work as expected."""
        self.client.post("/register", json={"username": "grace", "password": "Password123", "email": "grace@test.com"})
        self.client.post("/register", json={"username": "heidi", "password": "Password123"})

        # List users
        res = self.client.get("/users")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["count"], 2)

        # Single user
        res_single = self.client.get("/users/grace")
        self.assertEqual(res_single.status_code, 200)
        self.assertEqual(res_single.get_json()["user"]["email"], "grace@test.com")

        # Unknown user
        res_unknown = self.client.get("/users/nobody")
        self.assertEqual(res_unknown.status_code, 404)

    # -------------------------------------------------------------------------
    # Task CRUD Endpoints
    # -------------------------------------------------------------------------

    def test_create_task_success(self) -> None:
        """POST /tasks creates a new task and returns 201."""
        res = self.client.post(
            "/tasks",
            json={
                "title": "Refactor Codebase",
                "description": "Separate concerns into models, routes, utils",
                "status": "in_progress",
            },
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["task"]["title"], "Refactor Codebase")
        self.assertEqual(data["task"]["status"], "in_progress")
        self.assertIn("id", data["task"])

    def test_create_task_missing_title(self) -> None:
        """POST /tasks returns 400 Bad Request when title is absent."""
        res = self.client.post("/tasks", json={"description": "No title here"})
        self.assertEqual(res.status_code, 400)

    def test_get_task_by_id(self) -> None:
        """GET /tasks/<task_id> retrieves the specified task."""
        created = self.client.post("/tasks", json={"title": "Test Task"}).get_json()["task"]
        task_id = created["id"]

        res = self.client.get(f"/tasks/{task_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["task"]["title"], "Test Task")

        # Nonexistent task
        res_missing = self.client.get("/tasks/99999")
        self.assertEqual(res_missing.status_code, 404)

    def test_update_task(self) -> None:
        """PUT /tasks/<task_id> updates attributes."""
        created = self.client.post("/tasks", json={"title": "Original Title"}).get_json()["task"]
        task_id = created["id"]

        res = self.client.put(
            f"/tasks/{task_id}",
            json={"title": "Updated Title", "status": "completed"},
        )
        self.assertEqual(res.status_code, 200)
        updated = res.get_json()["task"]
        self.assertEqual(updated["title"], "Updated Title")
        self.assertEqual(updated["status"], "completed")

        # Invalid status
        res_invalid = self.client.put(f"/tasks/{task_id}", json={"status": "invalid_status"})
        self.assertEqual(res_invalid.status_code, 400)

    def test_delete_task(self) -> None:
        """DELETE /tasks/<task_id> deletes task and returns 200."""
        created = self.client.post("/tasks", json={"title": "To Delete"}).get_json()["task"]
        task_id = created["id"]

        res = self.client.delete(f"/tasks/{task_id}")
        self.assertEqual(res.status_code, 200)

        # Verify it's gone
        res_check = self.client.get(f"/tasks/{task_id}")
        self.assertEqual(res_check.status_code, 404)

        # Deleting again returns 404
        res_again = self.client.delete(f"/tasks/{task_id}")
        self.assertEqual(res_again.status_code, 404)

    def test_filter_tasks_by_status_and_user(self) -> None:
        """GET /tasks filters correctly by status and user_id."""
        reg_res = self.client.post("/register", json={"username": "ivan", "password": "Password123"})
        user_id = reg_res.get_json()["user"]["id"]

        self.client.post("/tasks", json={"title": "Task 1", "status": "pending", "user_id": user_id})
        self.client.post("/tasks", json={"title": "Task 2", "status": "completed", "user_id": user_id})
        self.client.post("/tasks", json={"title": "Task 3", "status": "pending"})

        # All tasks
        all_res = self.client.get("/tasks")
        self.assertEqual(all_res.get_json()["count"], 3)

        # Filter by status
        status_res = self.client.get("/tasks?status=completed")
        self.assertEqual(status_res.get_json()["count"], 1)
        self.assertEqual(status_res.get_json()["tasks"][0]["title"], "Task 2")

        # Filter by user_id
        user_res = self.client.get(f"/tasks?user_id={user_id}")
        self.assertEqual(user_res.get_json()["count"], 2)


if __name__ == "__main__":
    unittest.main()
