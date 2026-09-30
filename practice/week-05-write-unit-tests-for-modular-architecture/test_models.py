"""
test_models.py - Pytest Unit Tests for Task and User Domain Models.

Coverage:
- User model methods, attributes, properties, encapsulation, authentication, and task relationships.
- Task model methods, attributes, properties, encapsulation, status updates, validation, and serialization.
- Class-level storage/repository operations (create, get_by_id, get_by_username, get_by_email, get_all, delete_by_id, clear_all).
- Custom domain exceptions (ValidationError, UserAlreadyExistsError).
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timezone
import pytest

# Ensure current directory is in sys.path
current_dir = str(Path(__file__).resolve().parent)
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
def sample_user():
    """Fixture providing a registered user instance."""
    return User.register(
        username="testuser",
        password="ValidPassword123!",
        email="testuser@example.com",
    )


@pytest.fixture
def sample_task(sample_user):
    """Fixture providing a created task associated with sample_user."""
    return Task.create(
        title="Complete Documentation",
        description="Write comprehensive docstrings and README",
        status="in_progress",
        user_id=sample_user.id,
    )


# =============================================================================
# 1. Task Model Unit Tests
# =============================================================================

class TestTaskModel:
    """Test suite for Task class encapsulation, validation, properties, and repository methods."""

    def test_task_init_default_values(self):
        """Task initialized with required title has correct defaults."""
        task = Task(title="Buy Groceries")
        assert task.id == "1"
        assert task.title == "Buy Groceries"
        assert task.description == ""
        assert task.status == "pending"
        assert task.user_id is None
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)

    def test_task_init_with_custom_values(self):
        """Task initialized with all explicit parameters."""
        now = datetime.now(timezone.utc)
        task = Task(
            title="Design API",
            description="REST spec",
            status="completed",
            user_id="user-999",
            task_id="task-42",
            created_at=now,
            updated_at=now,
        )
        assert task.id == "task-42"
        assert task.title == "Design API"
        assert task.description == "REST spec"
        assert task.status == "completed"
        assert task.user_id == "user-999"
        assert task.created_at == now
        assert task.updated_at == now

    def test_task_title_getter_and_setter(self):
        """Task title can be updated and validated via property setter."""
        task = Task(title="Initial Title")
        task.title = "Updated Title"
        assert task.title == "Updated Title"

        with pytest.raises(ValidationError, match="cannot be empty"):
            task.title = ""

        with pytest.raises(ValidationError, match="cannot be empty"):
            task.title = "   "

    def test_task_description_getter_and_setter(self):
        """Task description can be updated via property setter."""
        task = Task(title="Sample Task")
        task.description = "New description"
        assert task.description == "New description"
        task.description = ""
        assert task.description == ""

    def test_task_status_setter_valid(self):
        """Valid statuses update the status attribute."""
        task = Task(title="Test Task")
        for valid in ["pending", "in_progress", "completed"]:
            task.status = valid
            assert task.status == valid

    def test_task_status_setter_invalid(self):
        """Invalid statuses raise ValidationError."""
        task = Task(title="Test Task")
        with pytest.raises(ValidationError, match="Invalid status"):
            task.status = "unknown_status"

    def test_task_user_id_setter(self):
        """user_id can be updated and cleared."""
        task = Task(title="Sample Task")
        task.user_id = "user-100"
        assert task.user_id == "user-100"
        task.user_id = None
        assert task.user_id is None

    def test_task_update_method(self):
        """task.update() method modifies multiple fields simultaneously."""
        task = Task(title="Initial Task", description="Old desc", status="pending")
        task.update(
            title="Refactored Title",
            description="New description",
            status="in_progress",
            user_id="user-123",
        )
        assert task.title == "Refactored Title"
        assert task.description == "New description"
        assert task.status == "in_progress"
        assert task.user_id == "user-123"

    def test_task_to_dict_serialization(self):
        """task.to_dict() returns a serializable dictionary with all fields."""
        task = Task(title="Dictionary Task", description="Detail", status="pending", user_id="u1")
        data = task.to_dict()
        assert data["id"] == task.id
        assert data["title"] == "Dictionary Task"
        assert data["description"] == "Detail"
        assert data["status"] == "pending"
        assert data["user_id"] == "u1"
        assert "created_at" in data
        assert "updated_at" in data

    def test_task_repr(self):
        """__repr__ returns readable diagnostic string."""
        task = Task(title="Repr Task")
        rep = repr(task)
        assert "<Task id=" in rep
        assert "title='Repr Task'" in rep

    def test_task_create_factory(self):
        """Task.create validates input and registers the task in storage."""
        task = Task.create(
            title="Factory Task",
            description="Created via create()",
            status="pending",
        )
        assert task.title == "Factory Task"
        assert Task.get_by_id(task.id) is task

    def test_task_create_missing_title_raises(self):
        """Task.create with empty title raises ValidationError."""
        with pytest.raises(ValidationError, match="Task title is required"):
            Task.create(title="")

    def test_task_repository_operations(self):
        """Task.get_by_id, get_all, delete_by_id, clear_all work as expected."""
        task1 = Task.create(title="Task 1")
        task2 = Task.create(title="Task 2")

        # get_by_id
        assert Task.get_by_id(task1.id) is task1
        assert Task.get_by_id(task2.id) is task2
        assert Task.get_by_id("non-existent-id") is None

        # get_all
        all_tasks = Task.get_all()
        assert len(all_tasks) == 2
        assert task1 in all_tasks
        assert task2 in all_tasks

        # delete_by_id
        assert Task.delete_by_id(task1.id) is True
        assert Task.get_by_id(task1.id) is None
        assert Task.delete_by_id("non-existent-id") is False
        assert len(Task.get_all()) == 1

        # clear_all
        Task.clear_all()
        assert len(Task.get_all()) == 0


# =============================================================================
# 2. User Model Unit Tests
# =============================================================================

class TestUserModel:
    """Test suite for User class encapsulation, authentication, properties, and repository methods."""

    def test_user_register_success(self):
        """User.register succeeds with valid credentials."""
        user = User.register(
            username="alice",
            password="Password123!",
            email="alice@example.com",
        )
        assert user.id is not None
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.password_hash != "Password123!"
        assert isinstance(user.created_at, datetime)

    def test_user_register_validation_errors(self):
        """User.register raises ValidationError for invalid username, password, or email."""
        # Short username
        with pytest.raises(ValidationError, match="at least 3 characters"):
            User.register(username="al", password="ValidPassword123!")

        # Short password
        with pytest.raises(ValidationError, match="at least 6 characters"):
            User.register(username="validuser", password="123")

        # Invalid email format
        with pytest.raises(ValidationError, match="Invalid email address format"):
            User.register(username="validuser", password="ValidPassword123!", email="not-an-email")

    def test_user_register_duplicate_username(self, sample_user):
        """Registering an already existing username raises UserAlreadyExistsError."""
        with pytest.raises(UserAlreadyExistsError, match="already registered"):
            User.register(
                username=sample_user.username.upper(),  # case-insensitive check
                password="AnotherPassword123!",
            )

    def test_user_register_duplicate_email(self, sample_user):
        """Registering an already existing email raises UserAlreadyExistsError."""
        with pytest.raises(UserAlreadyExistsError, match="already registered"):
            User.register(
                username="newuser_unique",
                password="AnotherPassword123!",
                email=sample_user.email.upper(),  # case-insensitive check
            )

    def test_user_authenticate_success(self, sample_user):
        """User.authenticate returns User instance when given valid credentials."""
        auth_user = User.authenticate(
            username="testuser",
            password="ValidPassword123!",
        )
        assert auth_user is not None
        assert auth_user.id == sample_user.id

    def test_user_authenticate_wrong_password(self, sample_user):
        """User.authenticate returns None for incorrect password."""
        auth_user = User.authenticate(username="testuser", password="WrongPassword!")
        assert auth_user is None

    def test_user_authenticate_nonexistent_user(self):
        """User.authenticate returns None for unknown username."""
        auth_user = User.authenticate(username="nonexistent", password="Password123!")
        assert auth_user is None

    def test_user_authenticate_empty_credentials(self):
        """User.authenticate returns None when username or password is empty."""
        assert User.authenticate("", "Password123!") is None
        assert User.authenticate("username", "") is None

    def test_user_check_password(self, sample_user):
        """user.check_password correctly validates candidate passwords."""
        assert sample_user.check_password("ValidPassword123!") is True
        assert sample_user.check_password("InvalidPassword") is False
        assert sample_user.check_password("") is False

    def test_user_create_task_and_get_tasks(self, sample_user):
        """User creates tasks and retrieves them via user.get_tasks()."""
        task1 = sample_user.create_task(title="User Task 1", description="First")
        task2 = sample_user.create_task(title="User Task 2", status="in_progress")

        assert task1.user_id == sample_user.id
        assert task2.user_id == sample_user.id

        user_tasks = sample_user.get_tasks()
        assert len(user_tasks) == 2
        assert task1 in user_tasks
        assert task2 in user_tasks

    def test_user_to_dict_serialization(self, sample_user):
        """user.to_dict() serializes user safely without exposing password hash."""
        sample_user.create_task(title="Dict Task")

        data_without_tasks = sample_user.to_dict(include_tasks=False)
        assert data_without_tasks["id"] == sample_user.id
        assert data_without_tasks["username"] == sample_user.username
        assert data_without_tasks["email"] == sample_user.email
        assert "password_hash" not in data_without_tasks
        assert "tasks" not in data_without_tasks

        data_with_tasks = sample_user.to_dict(include_tasks=True)
        assert "tasks" in data_with_tasks
        assert len(data_with_tasks["tasks"]) == 1
        assert data_with_tasks["tasks"][0]["title"] == "Dict Task"

    def test_user_repr(self, sample_user):
        """__repr__ returns readable diagnostic string."""
        rep = repr(sample_user)
        assert "<User id=" in rep
        assert f"username='{sample_user.username}'" in rep

    def test_user_repository_lookups(self, sample_user):
        """User lookup methods (get_by_id, get_by_username, get_by_email, get_all)."""
        assert User.get_by_id(sample_user.id) is sample_user
        assert User.get_by_username("TESTUSER") is sample_user
        assert User.get_by_email("TESTUSER@EXAMPLE.COM") is sample_user
        assert User.get_by_id("invalid-id") is None
        assert User.get_by_username("unknown") is None
        assert User.get_by_email("unknown@example.com") is None

        all_users = User.get_all()
        assert len(all_users) == 1
        assert sample_user in all_users

    def test_user_clear_all(self, sample_user):
        """User.clear_all resets all user indexes."""
        User.clear_all()
        assert len(User.get_all()) == 0
        assert User.get_by_id(sample_user.id) is None
        assert User.get_by_username(sample_user.username) is None
        assert User.get_by_email(sample_user.email) is None
