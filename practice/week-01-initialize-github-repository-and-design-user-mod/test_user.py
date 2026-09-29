"""
test_user.py - Comprehensive unit tests for User and Task classes in Week 1.

Verifies:
1. User initialization and input validations
2. Success criteria: User stores tasks in an array structure (Python list)
3. Basic password hashing and authentication checks
4. Task management operations (add, retrieve, remove, clear)
5. Task class attributes and serialization
"""
import pytest
from User import User
from Task import Task


def test_user_initialization():
    """Verify that a User instance initializes correctly with username and email."""
    user = User(username="alice", email="alice@example.com")
    assert user.username == "alice"
    assert user.email == "alice@example.com"
    assert user.password_hash == ""
    assert isinstance(user.tasks, list)
    assert len(user.tasks) == 0


def test_user_initialization_invalid_inputs():
    """Verify type checking and value validation for user initialization."""
    with pytest.raises(TypeError):
        User(username=123, email="test@example.com")  # type: ignore

    with pytest.raises(ValueError):
        User(username="", email="test@example.com")

    with pytest.raises(TypeError):
        User(username="alice", email=456)  # type: ignore

    with pytest.raises(ValueError):
        User(username="alice", email="invalid_email_no_at")


def test_user_task_array_storage():
    """Verify success criteria: User class stores tasks in an array structure."""
    user = User(username="bob", email="bob@example.com")

    # Success criteria verification: tasks attribute is an array (list)
    assert isinstance(user.tasks, list)
    assert len(user.tasks) == 0

    # Add tasks
    task1 = Task(title="Complete Week 01 assignment", description="Implement User model")
    task2 = {"id": 2, "title": "Review PR", "status": "pending"}
    task3 = "Simple string task"

    user.add_task(task1)
    user.add_task(task2)
    user.add_task(task3)

    assert len(user.tasks) == 3
    assert len(user) == 3
    assert user.get_tasks() == [task1, task2, task3]
    assert user[0] == task1
    assert user[1] == task2
    assert user[2] == task3


def test_user_task_removal_and_retrieval():
    """Verify task retrieval by id, removing tasks, and clearing tasks array."""
    user = User(username="charlie", email="charlie@example.com")
    task1 = Task(title="Write tests", task_id=101)
    task2 = {"id": 102, "title": "Deploy code"}

    user.add_task(task1)
    user.add_task(task2)

    assert user.get_task_by_id(101) == task1
    assert user.get_task_by_id(102) == task2
    assert user.get_task_by_id(999) is None

    # Remove task1
    assert user.remove_task(task1) is True
    assert len(user) == 1
    assert task1 not in user.tasks

    # Remove task2 by id
    assert user.remove_task(102) is True
    assert len(user) == 0

    # Removing non-existent task returns False
    assert user.remove_task("missing") is False

    # Clear tasks
    user.add_task(task1)
    assert len(user) == 1
    user.clear_tasks()
    assert len(user) == 0


def test_user_password_hashing():
    """Verify that password is automatically hashed and raw password is not stored."""
    raw_password = "SuperSecretPassword123!"
    user = User(username="dana", email="dana@example.com", password=raw_password)

    # Password hash is created
    assert user.password_hash != ""
    assert user.password_hash != raw_password
    assert raw_password not in user.password_hash

    # Verification works
    assert user.check_password(raw_password) is True
    assert user.check_password("WrongPassword") is False
    assert user.check_password("") is False


def test_user_password_update():
    """Verify that set_password updates the hash properly."""
    user = User(username="eve", email="eve@example.com")
    assert user.check_password("test") is False

    user.set_password("FirstPassword123")
    assert user.check_password("FirstPassword123") is True
    assert user.check_password("SecondPassword456") is False

    user.set_password("SecondPassword456")
    assert user.check_password("FirstPassword123") is False
    assert user.check_password("SecondPassword456") is True


def test_user_serialization():
    """Verify to_dict produces expected dictionary representation."""
    user = User(username="frank", email="frank@example.com", password="secretpassword", user_id=1)
    task = Task(title="Setup CI/CD", description="Configure actions", task_id=1)
    user.add_task(task)

    data = user.to_dict()
    assert data["id"] == 1
    assert data["username"] == "frank"
    assert data["email"] == "frank@example.com"
    assert "password" not in data
    assert "password_hash" not in data
    assert data["task_count"] == 1
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["title"] == "Setup CI/CD"


def test_task_model():
    """Verify Task model initialization, parsing, and status transitions."""
    task = Task(
        title="Scaffold backend",
        description="Initialize core models",
        due_date="2026-10-15",
    )
    assert task.title == "Scaffold backend"
    assert task.description == "Initialize core models"
    assert task.status == "pending"
    assert task.completed is False
    assert task.due_date is not None
    assert str(task.due_date) == "2026-10-15"

    task.mark_completed()
    assert task.completed is True
    assert task.status == "completed"

    task_dict = task.to_dict()
    assert task_dict["title"] == "Scaffold backend"
    assert task_dict["completed"] is True
