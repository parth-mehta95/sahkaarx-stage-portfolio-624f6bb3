"""
test_routes.py - Pytest Unit Tests for Flask API Route Handlers.

Coverage:
- Authentication endpoints: /register, /login, /logout, /users, /users/<username>
- Task CRUD endpoints: /tasks (GET, POST), /tasks/<task_id> (GET, PUT, PATCH, DELETE)
- Filtering query parameters (status, user_id)
- HTTP status code validation (200, 201, 400, 401, 404, 409)
- JSON payload responses and error message structures
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest
from flask import Flask
from flask.testing import FlaskClient

# Ensure current directory is in sys.path
current_dir = str(Path(__file__).resolve().parent)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from app import create_app
    from models import Task, User
except ImportError:  # pragma: no cover
    from .app import create_app
    from .models import Task, User


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def clean_repositories():
    """Reset repository storage before and after each test."""
    Task.clear_all()
    User.clear_all()
    yield
    Task.clear_all()
    User.clear_all()


@pytest.fixture
def app() -> Flask:
    """Create a configured Flask application for testing."""
    test_app = create_app({"TESTING": True})
    return test_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create Flask test client for sending mock HTTP requests."""
    return app.test_client()


@pytest.fixture
def sample_user() -> User:
    """Register and persist a sample user."""
    return User.register(
        username="route_tester",
        password="ValidPassword123!",
        email="route_tester@example.com",
    )


@pytest.fixture
def sample_task(sample_user: User) -> Task:
    """Create and persist a sample task."""
    return Task.create(
        title="Initial Route Task",
        description="Task created for route tests",
        status="pending",
        user_id=sample_user.id,
    )


# =============================================================================
# 1. Root & Discovery Tests
# =============================================================================

class TestDiscoveryEndpoints:
    """Verify application discovery and root health check routes."""

    def test_root_discovery(self, client: FlaskClient):
        """GET / returns 200 OK and modular architecture metadata."""
        res = client.get("/")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status_code"] == 200
        assert "service" in data
        assert "endpoints" in data


# =============================================================================
# 2. Authentication Route Tests
# =============================================================================

class TestAuthRoutes:
    """Verify all authentication and user management route handlers."""

    def test_register_success(self, client: FlaskClient):
        """POST /register returns 201 Created and user dictionary."""
        payload = {
            "username": "newuser",
            "password": "SecurePassword123!",
            "email": "newuser@example.com",
        }
        res = client.post("/register", json=payload)
        assert res.status_code == 201
        data = res.get_json()
        assert data["status_code"] == 201
        assert data["user"]["username"] == "newuser"
        assert data["user"]["email"] == "newuser@example.com"
        assert "password_hash" not in data["user"]

    def test_register_missing_username(self, client: FlaskClient):
        """POST /register without username returns 400 Bad Request."""
        res = client.post("/register", json={"password": "Password123!"})
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data
        assert "Username is required" in data["error"]

    def test_register_missing_password(self, client: FlaskClient):
        """POST /register without password returns 400 Bad Request."""
        res = client.post("/register", json={"username": "validname"})
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data
        assert "Password is required" in data["error"]

    def test_register_invalid_inputs(self, client: FlaskClient):
        """POST /register with invalid username/password/email returns 400 Bad Request."""
        # Short username
        res = client.post("/register", json={"username": "ab", "password": "Password123!"})
        assert res.status_code == 400

        # Short password
        res = client.post("/register", json={"username": "validname", "password": "123"})
        assert res.status_code == 400

        # Invalid email
        res = client.post(
            "/register",
            json={"username": "validname", "password": "Password123!", "email": "bademail"},
        )
        assert res.status_code == 400

    def test_register_duplicate_username(self, client: FlaskClient, sample_user: User):
        """POST /register with existing username returns 409 Conflict."""
        res = client.post(
            "/register",
            json={"username": sample_user.username, "password": "Password123!"},
        )
        assert res.status_code == 409
        data = res.get_json()
        assert "already registered" in data["error"]

    def test_register_duplicate_email(self, client: FlaskClient, sample_user: User):
        """POST /register with existing email returns 409 Conflict."""
        res = client.post(
            "/register",
            json={
                "username": "different_username",
                "password": "Password123!",
                "email": sample_user.email,
            },
        )
        assert res.status_code == 409
        data = res.get_json()
        assert "already registered" in data["error"]

    def test_login_success(self, client: FlaskClient, sample_user: User):
        """POST /login with valid credentials returns 200 OK and user object."""
        payload = {"username": "route_tester", "password": "ValidPassword123!"}
        res = client.post("/login", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["user"]["username"] == "route_tester"

    def test_login_missing_fields(self, client: FlaskClient):
        """POST /login with missing fields returns 400 Bad Request."""
        res = client.post("/login", json={"username": "route_tester"})
        assert res.status_code == 400

        res = client.post("/login", json={"password": "Password123!"})
        assert res.status_code == 400

    def test_login_invalid_credentials(self, client: FlaskClient, sample_user: User):
        """POST /login with wrong password returns 401 Unauthorized."""
        res = client.post(
            "/login",
            json={"username": "route_tester", "password": "WrongPassword!"},
        )
        assert res.status_code == 401
        data = res.get_json()
        assert "Invalid username or password" in data["error"]

    def test_login_unknown_user(self, client: FlaskClient):
        """POST /login with unregistered username returns 401 Unauthorized."""
        res = client.post(
            "/login",
            json={"username": "ghost_user", "password": "AnyPassword123!"},
        )
        assert res.status_code == 401

    def test_logout_endpoint(self, client: FlaskClient):
        """POST /logout returns 200 OK."""
        res = client.post("/logout")
        assert res.status_code == 200
        data = res.get_json()
        assert data["message"] == "Logged out successfully."

    def test_get_users_list(self, client: FlaskClient, sample_user: User):
        """GET /users returns 200 OK with list of all users."""
        res = client.get("/users")
        assert res.status_code == 200
        data = res.get_json()
        assert data["count"] == 1
        assert len(data["users"]) == 1
        assert data["users"][0]["username"] == sample_user.username

    def test_get_user_by_username_success(self, client: FlaskClient, sample_user: User):
        """GET /users/<username> returns 200 OK with user profile and associated tasks."""
        sample_user.create_task(title="Profile Task")
        res = client.get(f"/users/{sample_user.username}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["user"]["username"] == sample_user.username
        assert "tasks" in data["user"]
        assert len(data["user"]["tasks"]) == 1

    def test_get_user_by_username_not_found(self, client: FlaskClient):
        """GET /users/<username> returns 404 Not Found for non-existent user."""
        res = client.get("/users/non_existent_username")
        assert res.status_code == 404
        data = res.get_json()
        assert "not found" in data["error"].lower()


# =============================================================================
# 3. Task CRUD Route Tests
# =============================================================================

class TestTaskRoutes:
    """Verify all Task CRUD route handlers."""

    def test_create_task_success(self, client: FlaskClient):
        """POST /tasks returns 201 Created and creates standalone task."""
        payload = {
            "title": "Build Unit Tests",
            "description": "Test modular components",
            "status": "pending",
        }
        res = client.post("/tasks", json=payload)
        assert res.status_code == 201
        data = res.get_json()
        assert data["task"]["title"] == "Build Unit Tests"
        assert data["task"]["status"] == "pending"

    def test_create_task_with_user_association(self, client: FlaskClient, sample_user: User):
        """POST /tasks with user_id associates task with user."""
        payload = {
            "title": "User Specific Task",
            "description": "Linked to user",
            "user_id": sample_user.id,
            "status": "in_progress",
        }
        res = client.post("/tasks", json=payload)
        assert res.status_code == 201
        data = res.get_json()
        assert data["task"]["user_id"] == sample_user.id
        assert data["task"]["status"] == "in_progress"

    def test_create_task_missing_title(self, client: FlaskClient):
        """POST /tasks without title returns 400 Bad Request."""
        res = client.post("/tasks", json={"description": "Missing title"})
        assert res.status_code == 400
        data = res.get_json()
        assert "Task title is required" in data["error"]

    def test_create_task_invalid_status(self, client: FlaskClient):
        """POST /tasks with invalid status returns 400 Bad Request."""
        res = client.post("/tasks", json={"title": "Valid Title", "status": "bogus"})
        assert res.status_code == 400
        data = res.get_json()
        assert "Invalid status" in data["error"]

    def test_list_tasks(self, client: FlaskClient, sample_task: Task):
        """GET /tasks returns 200 OK and list of all tasks."""
        res = client.get("/tasks")
        assert res.status_code == 200
        data = res.get_json()
        assert data["count"] == 1
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["id"] == sample_task.id

    def test_list_tasks_filter_by_status(self, client: FlaskClient, sample_user: User):
        """GET /tasks?status=... filters tasks by status."""
        Task.create(title="Pending Task", status="pending")
        Task.create(title="Completed Task", status="completed")

        res_pending = client.get("/tasks?status=pending")
        assert res_pending.status_code == 200
        data_pending = res_pending.get_json()
        assert len(data_pending["tasks"]) == 1
        assert data_pending["tasks"][0]["title"] == "Pending Task"

        res_completed = client.get("/tasks?status=completed")
        assert res_completed.status_code == 200
        data_completed = res_completed.get_json()
        assert len(data_completed["tasks"]) == 1
        assert data_completed["tasks"][0]["title"] == "Completed Task"

    def test_list_tasks_filter_by_user_id(self, client: FlaskClient, sample_user: User):
        """GET /tasks?user_id=... filters tasks by associated user ID."""
        user2 = User.register(username="user2", password="Password123!")
        Task.create(title="User 1 Task", user_id=sample_user.id)
        Task.create(title="User 2 Task", user_id=user2.id)

        res = client.get(f"/tasks?user_id={sample_user.id}")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["title"] == "User 1 Task"

    def test_get_task_by_id_success(self, client: FlaskClient, sample_task: Task):
        """GET /tasks/<task_id> returns 200 OK and task details."""
        res = client.get(f"/tasks/{sample_task.id}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["task"]["id"] == sample_task.id
        assert data["task"]["title"] == sample_task.title

    def test_get_task_by_id_not_found(self, client: FlaskClient):
        """GET /tasks/<task_id> returns 404 Not Found for non-existent ID."""
        res = client.get("/tasks/non_existent_task_id")
        assert res.status_code == 404
        data = res.get_json()
        assert "not found" in data["error"].lower()

    def test_update_task_put_success(self, client: FlaskClient, sample_task: Task):
        """PUT /tasks/<task_id> returns 200 OK and updates task fields."""
        update_payload = {
            "title": "Updated Task Title",
            "description": "Updated Description",
            "status": "completed",
        }
        res = client.put(f"/tasks/{sample_task.id}", json=update_payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["task"]["title"] == "Updated Task Title"
        assert data["task"]["status"] == "completed"

    def test_update_task_patch_success(self, client: FlaskClient, sample_task: Task):
        """PATCH /tasks/<task_id> returns 200 OK for partial updates."""
        res = client.patch(f"/tasks/{sample_task.id}", json={"status": "in_progress"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["task"]["status"] == "in_progress"
        assert data["task"]["title"] == sample_task.title

    def test_update_task_empty_payload(self, client: FlaskClient, sample_task: Task):
        """PUT /tasks/<task_id> with empty payload returns 400 Bad Request."""
        res = client.put(f"/tasks/{sample_task.id}", json={})
        assert res.status_code == 400
        data = res.get_json()
        assert "No update fields provided" in data["error"]

    def test_update_task_invalid_data(self, client: FlaskClient, sample_task: Task):
        """PUT /tasks/<task_id> with invalid data returns 400 Bad Request."""
        res = client.put(f"/tasks/{sample_task.id}", json={"status": "invalid_status"})
        assert res.status_code == 400
        data = res.get_json()
        assert "Invalid status" in data["error"]

    def test_update_task_not_found(self, client: FlaskClient):
        """PUT /tasks/<task_id> for non-existent task returns 404 Not Found."""
        res = client.put("/tasks/non_existent_id", json={"title": "Updated"})
        assert res.status_code == 404
        data = res.get_json()
        assert "not found" in data["error"].lower()

    def test_delete_task_success(self, client: FlaskClient, sample_task: Task):
        """DELETE /tasks/<task_id> returns 200 OK and deletes task."""
        res = client.delete(f"/tasks/{sample_task.id}")
        assert res.status_code == 200
        data = res.get_json()
        assert "deleted successfully" in data["message"]

        # Confirm task is gone
        get_res = client.get(f"/tasks/{sample_task.id}")
        assert get_res.status_code == 404

    def test_delete_task_not_found(self, client: FlaskClient):
        """DELETE /tasks/<task_id> for non-existent ID returns 404 Not Found."""
        res = client.delete("/tasks/non_existent_task_id")
        assert res.status_code == 404
        data = res.get_json()
        assert "not found" in data["error"].lower()

    def test_prefixed_routes(self, client: FlaskClient):
        """Verify routes also function under prefixes (/auth and /api)."""
        res_auth = client.post("/auth/register", json={"username": "prefix_user", "password": "Password123!"})
        assert res_auth.status_code == 201

        res_tasks = client.get("/api/tasks")
        assert res_tasks.status_code == 200
