"""
test_routes.py - Pytest Unit Tests for Flask API Route Handlers.

Coverage:
- Root discovery endpoint (GET /)
- Authentication endpoints: /register, /login, /logout, /users, /users/<username>
- Task CRUD endpoints: /tasks (GET, POST), /tasks/<task_id> (GET, PUT, PATCH, DELETE)
- Filtering query parameters (status, user_id)
- HTTP status code validation (200, 201, 400, 401, 404, 405, 409)
- JSON payload response validation and error handling
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest
from flask import Flask
from flask.testing import FlaskClient

# Ensure current directory is in sys.path
current_dir: str = str(Path(__file__).resolve().parent)
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
        title="Sample Route Task",
        description="Task used for route testing",
        status="pending",
        user_id=sample_user.id,
    )


# =============================================================================
# 1. Root & Discovery Tests
# =============================================================================

class TestDiscoveryEndpoints:
    """Tests for system discovery and root endpoints."""

    def test_root_discovery(self, client: FlaskClient) -> None:
        """GET / returns status 200 with service description."""
        res = client.get("/")
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["success"] is True
        assert "service" in payload
        assert "endpoints" in payload


# =============================================================================
# 2. Authentication Route Tests
# =============================================================================

class TestAuthRoutes:
    """Tests for authentication and user management endpoints."""

    def test_register_success(self, client: FlaskClient) -> None:
        """POST /register returns 201 Created with user details."""
        res = client.post(
            "/register",
            data=json.dumps(
                {
                    "username": "new_developer",
                    "password": "StrongPassword123!",
                    "email": "dev@example.com",
                }
            ),
            content_type="application/json",
        )
        assert res.status_code == 201
        payload = res.get_json()
        assert payload["success"] is True
        assert payload["user"]["username"] == "new_developer"
        assert "password" not in payload["user"]

    def test_register_missing_fields(self, client: FlaskClient) -> None:
        """POST /register returns 400 Bad Request when required fields are missing."""
        # Missing username
        res = client.post(
            "/register",
            data=json.dumps({"password": "pass", "email": "a@b.com"}),
            content_type="application/json",
        )
        assert res.status_code == 400

        # Missing password
        res = client.post(
            "/register",
            data=json.dumps({"username": "user", "email": "a@b.com"}),
            content_type="application/json",
        )
        assert res.status_code == 400

        # Missing email
        res = client.post(
            "/register",
            data=json.dumps({"username": "user", "password": "password"}),
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_register_validation_failure(self, client: FlaskClient) -> None:
        """POST /register returns 400 Bad Request on invalid format."""
        res = client.post(
            "/register",
            data=json.dumps(
                {
                    "username": "ab",  # Too short
                    "password": "123",
                    "email": "not-an-email",
                }
            ),
            content_type="application/json",
        )
        assert res.status_code == 400
        payload = res.get_json()
        assert payload["success"] is False
        assert "error" in payload

    def test_register_duplicate_conflict(self, client: FlaskClient, sample_user: User) -> None:
        """POST /register returns 409 Conflict when username or email already exists."""
        res = client.post(
            "/register",
            data=json.dumps(
                {
                    "username": sample_user.username,
                    "password": "AnotherPassword123!",
                    "email": "different@example.com",
                }
            ),
            content_type="application/json",
        )
        assert res.status_code == 409
        payload = res.get_json()
        assert payload["success"] is False

    def test_login_success(self, client: FlaskClient, sample_user: User) -> None:
        """POST /login returns 200 OK on valid credentials."""
        res = client.post(
            "/login",
            data=json.dumps(
                {
                    "username": sample_user.username,
                    "password": "ValidPassword123!",
                }
            ),
            content_type="application/json",
        )
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["success"] is True
        assert payload["authenticated"] is True
        assert payload["user"]["username"] == sample_user.username

    def test_login_invalid_credentials(self, client: FlaskClient, sample_user: User) -> None:
        """POST /login returns 401 Unauthorized on incorrect password."""
        res = client.post(
            "/login",
            data=json.dumps(
                {
                    "username": sample_user.username,
                    "password": "WrongPassword",
                }
            ),
            content_type="application/json",
        )
        assert res.status_code == 401
        payload = res.get_json()
        assert payload["success"] is False

    def test_login_missing_fields(self, client: FlaskClient) -> None:
        """POST /login returns 400 Bad Request when fields are missing."""
        res = client.post(
            "/login",
            data=json.dumps({"username": ""}),
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_logout(self, client: FlaskClient) -> None:
        """POST /logout returns 200 OK."""
        res = client.post("/logout")
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["authenticated"] is False

    def test_list_users(self, client: FlaskClient, sample_user: User) -> None:
        """GET /users returns 200 OK and list of users."""
        res = client.get("/users")
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["count"] == 1
        assert payload["users"][0]["username"] == sample_user.username

    def test_get_user_profile(self, client: FlaskClient, sample_user: User) -> None:
        """GET /users/<username> returns 200 OK or 404 Not Found."""
        res = client.get(f"/users/{sample_user.username}")
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["user"]["username"] == sample_user.username
        assert "tasks" in payload["user"]

        # Missing user
        res404 = client.get("/users/nonexistent_person")
        assert res404.status_code == 404


# =============================================================================
# 3. Task Route Tests
# =============================================================================

class TestTaskRoutes:
    """Tests for task CRUD and filtering endpoints."""

    def test_list_tasks_empty_and_populated(self, client: FlaskClient, sample_task: Task) -> None:
        """GET /tasks returns 200 OK with all tasks."""
        res = client.get("/tasks")
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["count"] == 1
        assert payload["tasks"][0]["id"] == sample_task.id

    def test_list_tasks_filter_by_user_and_status(
        self,
        client: FlaskClient,
        sample_user: User,
    ) -> None:
        """GET /tasks?user_id=...&status=... filters results."""
        Task.create(title="Task A", status="pending", user_id=sample_user.id)
        Task.create(title="Task B", status="completed", user_id=sample_user.id)
        Task.create(title="Task C", status="pending", user_id="other-user")

        # Filter by status
        res = client.get("/tasks?status=completed")
        assert res.status_code == 200
        assert res.get_json()["count"] == 1

        # Filter by user
        res = client.get(f"/tasks?user_id={sample_user.id}")
        assert res.status_code == 200
        assert res.get_json()["count"] == 2

        # Invalid status filter
        res_invalid = client.get("/tasks?status=unknown_bad_status")
        assert res_invalid.status_code == 400

    def test_create_task_success(self, client: FlaskClient, sample_user: User) -> None:
        """POST /tasks creates a new task and returns 201 Created."""
        res = client.post(
            "/tasks",
            data=json.dumps(
                {
                    "title": "Build Finalized App",
                    "description": "Production ready with type hints",
                    "status": "pending",
                    "user_id": sample_user.id,
                }
            ),
            content_type="application/json",
        )
        assert res.status_code == 201
        payload = res.get_json()
        assert payload["task"]["title"] == "Build Finalized App"
        assert payload["task"]["user_id"] == sample_user.id

    def test_create_task_missing_title(self, client: FlaskClient) -> None:
        """POST /tasks returns 400 Bad Request when title is missing or empty."""
        res = client.post(
            "/tasks",
            data=json.dumps({"description": "No title here"}),
            content_type="application/json",
        )
        assert res.status_code == 400

        res_empty = client.post(
            "/tasks",
            data=json.dumps({"title": "   "}),
            content_type="application/json",
        )
        assert res_empty.status_code == 400

    def test_get_task_by_id(self, client: FlaskClient, sample_task: Task) -> None:
        """GET /tasks/<task_id> returns 200 OK or 404 Not Found."""
        res = client.get(f"/tasks/{sample_task.id}")
        assert res.status_code == 200
        assert res.get_json()["task"]["id"] == sample_task.id

        res_missing = client.get("/tasks/999999")
        assert res_missing.status_code == 404

    def test_update_task(self, client: FlaskClient, sample_task: Task) -> None:
        """PUT and PATCH /tasks/<task_id> update task and return 200 OK."""
        res = client.put(
            f"/tasks/{sample_task.id}",
            data=json.dumps(
                {
                    "title": "Renamed Task",
                    "status": "completed",
                }
            ),
            content_type="application/json",
        )
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["task"]["title"] == "Renamed Task"
        assert payload["task"]["status"] == "completed"

        # Update empty body
        res_empty = client.put(
            f"/tasks/{sample_task.id}",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert res_empty.status_code == 400

        # Update non-existent
        res_missing = client.put(
            "/tasks/999999",
            data=json.dumps({"title": "Ghost"}),
            content_type="application/json",
        )
        assert res_missing.status_code == 404

    def test_delete_task(self, client: FlaskClient, sample_task: Task) -> None:
        """DELETE /tasks/<task_id> returns 200 OK or 404 Not Found."""
        res = client.delete(f"/tasks/{sample_task.id}")
        assert res.status_code == 200
        assert Task.get_by_id(sample_task.id) is None

        # Repeat delete returns 404
        res_repeat = client.delete(f"/tasks/{sample_task.id}")
        assert res_repeat.status_code == 404


# =============================================================================
# 4. Error Handler Tests
# =============================================================================

class TestErrorHandlers:
    """Tests for custom Flask error handlers."""

    def test_404_not_found_route(self, client: FlaskClient) -> None:
        """Accessing a non-existent URL returns 404 JSON."""
        res = client.get("/completely/unknown/endpoint")
        assert res.status_code == 404
        payload = res.get_json()
        assert payload["success"] is False
        assert "Resource Not Found" in payload["error"]

    def test_405_method_not_allowed(self, client: FlaskClient) -> None:
        """Sending invalid HTTP method returns 405 JSON."""
        res = client.post("/")  # Root only supports GET
        assert res.status_code == 405
        payload = res.get_json()
        assert payload["success"] is False
        assert "Method Not Allowed" in payload["error"]
