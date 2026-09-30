"""
test_models.py - Pytest Unit Tests for Task and User Domain Models.

Coverage:
- Task domain entity: initialization, properties, setters, invariants, serialization.
- User domain entity: registration, authentication, password management, relationships.
- Persistence operations: create, get_by_id, filter_by, delete_by_id, clear_all, cascading deletes.
- Custom exceptions: ValidationError, UserAlreadyExistsError.
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timezone
import pytest

# Ensure current directory is in sys.path
current_dir: str = str(Path(__file__).resolve().parent)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from models import Task, User
    from utils import (
        AuthenticationError,
        NotFoundError,
        UserAlreadyExistsError,
        ValidationError,
    )
except ImportError:  # pragma: no cover
    from .models import Task, User
    from .utils import (
        AuthenticationError,
        NotFoundError,
        UserAlreadyExistsError,
        ValidationError,
    )


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def clean_repositories():
    """Reset class-level in-memory storage before and after each test."""
    Task.clear_all()
    User.clear_all()
    yield
    Task.clear_all()
    User.clear_all()


@pytest.fixture
def sample_user() -> User:
    """Fixture providing a registered user instance."""
    return User.register(
        username="testuser",
        password="ValidPassword123!",
        email="testuser@example.com",
    )


@pytest.fixture
def sample_task(sample_user: User) -> Task:
    """Fixture providing a created task associated with sample_user."""
    return Task.create(
        title="Complete Test Suite",
        description="Write 70%+ coverage pytest unit tests",
        status="pending",
        user_id=sample_user.id,
    )


# =============================================================================
# 1. Task Domain Model Tests
# =============================================================================

class TestTaskModel:
    """Test suite for the Task domain model."""

    def test_task_init_default(self) -> None:
        """Test default values on task initialization."""
        task = Task(title="Default Task")
        assert task.id is not None
        assert task.title == "Default Task"
        assert task.description == ""
        assert task.status == "pending"
        assert task.completed is False
        assert task.user_id is None
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)
        assert task in Task.get_all()

    def test_task_init_custom_parameters(self) -> None:
        """Test custom parameters on task initialization."""
        custom_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        task = Task(
            title="Custom Task",
            description="Detailed Description",
            status="in_progress",
            user_id="user-42",
            task_id="999",
            completed=False,
            created_at=custom_time,
            updated_at=custom_time,
        )
        assert task.id == "999"
        assert task.title == "Custom Task"
        assert task.description == "Detailed Description"
        assert task.status == "in_progress"
        assert task.completed is False
        assert task.user_id == "user-42"
        assert task.created_at == custom_time

    def test_task_properties_and_setters(self) -> None:
        """Test encapsulated properties and their setters."""
        task = Task(title="Initial Title", description="Old Desc")

        task.title = "Updated Title"
        assert task.title == "Updated Title"

        task.description = "Updated Description"
        assert task.description == "Updated Description"

        task.status = "completed"
        assert task.status == "completed"
        assert task.completed is True

        task.completed = False
        assert task.completed is False
        assert task.status == "pending"

        task.user_id = "user-100"
        assert task.user_id == "user-100"

    def test_task_title_validation_empty(self) -> None:
        """Test that setting an empty title raises ValidationError."""
        task = Task(title="Valid Title")
        with pytest.raises(ValidationError, match="cannot be empty"):
            task.title = ""

        with pytest.raises(ValidationError, match="cannot be empty"):
            task.title = "   "

    def test_task_status_validation_invalid(self) -> None:
        """Test that invalid status strings raise ValidationError."""
        task = Task(title="Valid Task")
        with pytest.raises(ValidationError, match="Invalid task status"):
            task.status = "invalid_status"

    def test_task_update_multiple_fields(self) -> None:
        """Test bulk updating task fields."""
        task = Task(title="Original", description="Old")
        task.update(
            title="New Title",
            description="New Description",
            status="in_progress",
            completed=False,
            user_id="user-55",
        )
        assert task.title == "New Title"
        assert task.description == "New Description"
        assert task.status == "in_progress"
        assert task.user_id == "user-55"

    def test_task_mark_completed(self) -> None:
        """Test mark_completed state transition."""
        task = Task(title="Pending Work", status="pending")
        assert task.completed is False
        task.mark_completed()
        assert task.completed is True
        assert task.status == "completed"

    def test_task_to_dict_and_repr(self) -> None:
        """Test dictionary serialization and debug string representation."""
        task = Task(title="Dict Task", description="Serialization test")
        data = task.to_dict()
        assert data["id"] == task.id
        assert data["title"] == "Dict Task"
        assert data["description"] == "Serialization test"
        assert data["status"] == "pending"
        assert data["completed"] is False
        assert "created_at" in data
        assert "updated_at" in data

        rep = repr(task)
        assert "Dict Task" in rep
        assert "Task" in rep

    def test_task_repository_methods(self, sample_user: User) -> None:
        """Test class repository operations."""
        t1 = Task.create(title="Task One", user_id=sample_user.id, status="pending")
        t2 = Task.create(title="Task Two", user_id=sample_user.id, status="completed")
        t3 = Task.create(title="Task Three", user_id="other-user", status="pending")

        # get_by_id
        assert Task.get_by_id(t1.id) == t1
        assert Task.get_by_id("non-existent-id") is None

        # get_all
        all_tasks = Task.get_all()
        assert len(all_tasks) == 3

        # filter_by
        user_tasks = Task.filter_by(user_id=sample_user.id)
        assert len(user_tasks) == 2
        assert t3 not in user_tasks

        pending_tasks = Task.filter_by(status="pending")
        assert len(pending_tasks) == 2

        user_completed = Task.filter_by(user_id=sample_user.id, status="completed")
        assert len(user_completed) == 1
        assert user_completed[0] == t2

        # delete_by_id
        assert Task.delete_by_id(t1.id) is True
        assert Task.get_by_id(t1.id) is None
        assert Task.delete_by_id("non-existent") is False


# =============================================================================
# 2. User Domain Model Tests
# =============================================================================

class TestUserModel:
    """Test suite for the User domain model."""

    def test_user_registration_success(self) -> None:
        """Test registering a valid user."""
        user = User.register(
            username="alice_dev",
            password="StrongPassword123!",
            email="alice@example.com",
        )
        assert user.id is not None
        assert user.username == "alice_dev"
        assert user.email == "alice@example.com"
        assert user.check_password("StrongPassword123!") is True
        assert user.check_password("WrongPassword") is False
        assert isinstance(user.created_at, datetime)

    def test_user_registration_duplicate_username(self, sample_user: User) -> None:
        """Test that registering duplicate username raises UserAlreadyExistsError."""
        with pytest.raises(UserAlreadyExistsError, match="already registered"):
            User.register(
                username=sample_user.username,
                password="AnotherPassword123!",
                email="distinct@example.com",
            )

    def test_user_registration_duplicate_email(self, sample_user: User) -> None:
        """Test that registering duplicate email raises UserAlreadyExistsError."""
        with pytest.raises(UserAlreadyExistsError, match="already registered"):
            User.register(
                username="distinct_user",
                password="AnotherPassword123!",
                email=sample_user.email,
            )

    def test_user_registration_validation_errors(self) -> None:
        """Test validation rules for invalid usernames, passwords, and emails."""
        with pytest.raises(ValidationError, match="at least 3 characters"):
            User.register(username="ab", password="ValidPass123", email="user@example.com")

        with pytest.raises(ValidationError, match="at least 6 characters"):
            User.register(username="validuser", password="123", email="user@example.com")

        with pytest.raises(ValidationError, match="Invalid email"):
            User.register(username="validuser", password="ValidPass123", email="notanemail")

    def test_user_authentication(self, sample_user: User) -> None:
        """Test user authentication flows."""
        auth_user = User.authenticate(sample_user.username, "ValidPassword123!")
        assert auth_user is not None
        assert auth_user.id == sample_user.id

        assert User.authenticate(sample_user.username, "WrongPassword") is None
        assert User.authenticate("nonexistent_user", "AnyPassword") is None
        assert User.authenticate("", "Password") is None
        assert User.authenticate("user", "") is None

    def test_user_set_password(self, sample_user: User) -> None:
        """Test updating user password."""
        sample_user.set_password("NewPassword456!")
        assert sample_user.check_password("NewPassword456!") is True
        assert sample_user.check_password("ValidPassword123!") is False

    def test_user_task_relationships(self, sample_user: User) -> None:
        """Test creating and retrieving user-owned tasks."""
        t1 = sample_user.create_task(title="Alice Task 1", status="pending")
        t2 = sample_user.create_task(title="Alice Task 2", status="completed")

        tasks = sample_user.get_tasks()
        assert len(tasks) == 2
        assert t1 in tasks
        assert t2 in tasks

    def test_user_to_dict_and_repr(self, sample_user: User) -> None:
        """Test dictionary serialization and safe password exclusion."""
        sample_user.create_task(title="Owned Task")
        simple_dict = sample_user.to_dict(include_tasks=False)
        assert simple_dict["username"] == sample_user.username
        assert simple_dict["email"] == sample_user.email
        assert "password" not in simple_dict
        assert "password_hash" not in simple_dict
        assert "tasks" not in simple_dict

        detailed_dict = sample_user.to_dict(include_tasks=True)
        assert "tasks" in detailed_dict
        assert len(detailed_dict["tasks"]) == 1

        rep = repr(sample_user)
        assert sample_user.username in rep

    def test_user_repository_queries(self, sample_user: User) -> None:
        """Test repository lookup methods."""
        assert User.get_by_id(sample_user.id) == sample_user
        assert User.get_by_username(sample_user.username) == sample_user
        assert User.get_by_email(sample_user.email) == sample_user
        assert len(User.get_all()) == 1

        # Non-existent lookups
        assert User.get_by_id("non-existent") is None
        assert User.get_by_username("ghost") is None
        assert User.get_by_email("ghost@example.com") is None

    def test_user_cascade_delete(self, sample_user: User) -> None:
        """Test that deleting a user cascade-deletes their tasks."""
        sample_user.create_task(title="Owned Task 1")
        sample_user.create_task(title="Owned Task 2")
        orphan_task = Task.create(title="Orphan Task", user_id="someone-else")

        assert len(Task.get_all()) == 3
        deleted = User.delete_by_id(sample_user.id)
        assert deleted is True

        assert User.get_by_id(sample_user.id) is None
        remaining_tasks = Task.get_all()
        assert len(remaining_tasks) == 1
        assert remaining_tasks[0].id == orphan_task.id
