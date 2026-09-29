"""tests/test_task_manager.py - Unit and integration tests for Task Manager models and routes."""
import inspect
from typing import get_type_hints
import pytest
from app import create_app
from models import db, Task, User


@pytest.fixture
def app():
    """Create test application using an in-memory SQLite database."""
    test_app = create_app(database_uri="sqlite:///:memory:")
    test_app.config["TESTING"] = True

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client fixture."""
    return app.test_client()


# ==========================================================
# 1. Type Hint Tests
# ==========================================================


def test_models_have_type_hints():
    """Verify that User and Task methods have type hints on all parameters and return values."""
    user_methods = [
        User.__init__,
        User.set_password,
        User.check_password,
        User.register,
        User.authenticate,
        User.get_tasks,
        User.to_dict,
    ]
    for method in user_methods:
        hints = get_type_hints(method)
        assert "return" in hints, f"Missing return type hint in {method.__name__}"
        sig = inspect.signature(method)
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            assert param_name in hints, f"Missing type hint for '{param_name}' in {method.__name__}"

    task_methods = [
        Task.__init__,
        Task._parse_date,
        Task.update,
        Task.mark_completed,
        Task.to_dict,
    ]
    for method in task_methods:
        hints = get_type_hints(method)
        assert "return" in hints, f"Missing return type hint in {method.__name__}"
        sig = inspect.signature(method)
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            assert param_name in hints, f"Missing type hint for '{param_name}' in {method.__name__}"


# ==========================================================
# 2. Model Logic Tests
# ==========================================================


def test_user_model(app):
    """Test User creation, password hashing, and authentication."""
    with app.app_context():
        user = User.register(username="alice", email="alice@example.com", password="securepass123")
        assert user.id is not None
        assert user.username == "alice"
        assert user.check_password("securepass123") is True
        assert user.check_password("wrongpass") is False

        auth_user = User.authenticate(username="alice", password="securepass123")
        assert auth_user is not None
        assert auth_user.id == user.id

        assert User.authenticate(username="alice", password="wrongpass") is None
        assert User.authenticate(username="nonexistent", password="any") is None


def test_task_model(app):
    """Test Task creation, update, and date parsing."""
    with app.app_context():
        user = User.register(username="bob", email="bob@example.com", password="pwd")
        task = Task(
            title="Complete project",
            description="Week 7 refactor",
            due_date="2026-10-15",
            user_id=user.id,
        )
        db.session.add(task)
        db.session.commit()

        assert task.id is not None
        assert task.due_date.isoformat() == "2026-10-15"
        assert task.completed is False
        assert task.status == "pending"

        task.mark_completed()
        assert task.completed is True
        assert task.status == "completed"

        task.update(title="Updated project title", due_date="2026-11-01")
        assert task.title == "Updated project title"
        assert task.due_date.isoformat() == "2026-11-01"


# ==========================================================
# 3. Route Validation Tests (Task Creation)
# ==========================================================


def test_create_task_success(client):
    """Verify successful task creation with valid inputs."""
    payload = {
        "title": "Buy groceries",
        "description": "Milk, eggs, and bread",
        "due_date": "2026-10-20",
        "status": "pending",
    }
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["id"] is not None
    assert data["title"] == "Buy groceries"
    assert data["due_date"] == "2026-10-20"


def test_create_task_rejects_missing_title(client):
    """Verify task creation is rejected when title is missing."""
    response = client.post("/tasks", json={"description": "No title provided"})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Title is required" in data["error"]


def test_create_task_rejects_empty_title(client):
    """Verify task creation is rejected when title is empty or whitespace."""
    response = client.post("/tasks", json={"title": ""})
    assert response.status_code == 400
    assert "Title cannot be empty" in response.get_json()["error"]

    response2 = client.post("/tasks", json={"title": "   "})
    assert response2.status_code == 400
    assert "Title cannot be empty" in response2.get_json()["error"]


def test_create_task_rejects_invalid_date_format(client):
    """Verify task creation is rejected with malformed date strings."""
    invalid_dates = [
        "not-a-date",
        "10-20-2026",
        "2026/10/20",
        "2026-02-31",  # Invalid calendar day
        "2026-13-01",  # Invalid month
    ]
    for bad_date in invalid_dates:
        response = client.post("/tasks", json={"title": "Task", "due_date": bad_date})
        assert response.status_code == 400
        assert "Invalid date format" in response.get_json()["error"]


def test_create_task_rejects_non_string_date(client):
    """Verify task creation is rejected if due_date is not a string."""
    response = client.post("/tasks", json={"title": "Task", "due_date": 20261020})
    assert response.status_code == 400
    assert "Due date must be a string" in response.get_json()["error"]


def test_create_task_rejects_non_json(client):
    """Verify task creation is rejected if request body is not JSON."""
    response = client.post("/tasks", data="plain text", content_type="text/plain")
    assert response.status_code == 400
    assert "valid JSON" in response.get_json()["error"]


# ==========================================================
# 4. Route Validation Tests (Task Updates)
# ==========================================================


def test_update_task_validation(client):
    """Verify input validation on task updates."""
    # Create valid task first
    res = client.post("/tasks", json={"title": "Original Title"})
    assert res.status_code == 201
    task_id = res.get_json()["id"]

    # Reject empty title on update
    res_empty = client.put(f"/tasks/{task_id}", json={"title": "  "})
    assert res_empty.status_code == 400
    assert "Title cannot be empty" in res_empty.get_json()["error"]

    # Reject invalid date on update
    res_bad_date = client.put(f"/tasks/{task_id}", json={"due_date": "invalid-date"})
    assert res_bad_date.status_code == 400
    assert "Invalid date format" in res_bad_date.get_json()["error"]

    # Valid update
    res_valid = client.put(
        f"/tasks/{task_id}",
        json={"title": "Updated Title", "due_date": "2026-12-31", "completed": True},
    )
    assert res_valid.status_code == 200
    updated_data = res_valid.get_json()
    assert updated_data["title"] == "Updated Title"
    assert updated_data["due_date"] == "2026-12-31"
    assert updated_data["completed"] is True


# ==========================================================
# 5. CRUD and Auth Endpoint Tests
# ==========================================================


def test_task_crud_operations(client):
    """Test full CRUD operations on tasks."""
    # GET empty
    res = client.get("/tasks")
    assert res.status_code == 200
    assert res.get_json() == []

    # POST create
    res = client.post("/tasks", json={"title": "Task 1", "due_date": "2026-10-01"})
    task_id = res.get_json()["id"]

    # GET single
    res = client.get(f"/tasks/{task_id}")
    assert res.status_code == 200
    assert res.get_json()["title"] == "Task 1"

    # GET 404 for non-existent
    res = client.get("/tasks/99999")
    assert res.status_code == 404

    # DELETE
    res = client.delete(f"/tasks/{task_id}")
    assert res.status_code == 200

    # Verify deleted
    res = client.get(f"/tasks/{task_id}")
    assert res.status_code == 404


def test_auth_and_user_tasks(client):
    """Test user registration, login, and user-associated tasks."""
    reg_res = client.post(
        "/register",
        json={"username": "charlie", "email": "charlie@example.com", "password": "pass"},
    )
    assert reg_res.status_code == 201
    user_id = reg_res.get_json()["id"]

    # Duplicate username rejected
    dup_res = client.post(
        "/register",
        json={"username": "charlie", "email": "other@example.com", "password": "pass"},
    )
    assert dup_res.status_code == 400

    # Login
    login_res = client.post("/login", json={"username": "charlie", "password": "pass"})
    assert login_res.status_code == 200

    # Login failure
    login_fail = client.post("/login", json={"username": "charlie", "password": "wrong"})
    assert login_fail.status_code == 401

    # Create task for user
    client.post("/tasks", json={"title": "User task", "user_id": user_id})

    # Retrieve user tasks
    user_tasks_res = client.get(f"/users/{user_id}/tasks")
    assert user_tasks_res.status_code == 200
    tasks = user_tasks_res.get_json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "User task"
