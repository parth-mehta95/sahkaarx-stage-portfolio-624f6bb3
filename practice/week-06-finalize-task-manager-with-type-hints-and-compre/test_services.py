"""
test_services.py - Pytest Unit Tests for TaskManager Service Layer.

Coverage:
- UserService: registration, credential validation, authentication, lookup queries, deletion.
- TaskService: task creation, association with users, filtering, updates, status transitions, deletion.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

# Ensure current directory is in sys.path
current_dir: str = str(Path(__file__).resolve().parent)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from models import Task, User, UserAlreadyExistsError, ValidationError
    from services import TaskService, UserService
except ImportError:  # pragma: no cover
    from .models import Task, User, UserAlreadyExistsError, ValidationError
    from .services import TaskService, UserService


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def clean_repositories():
    """Reset repositories before and after every test."""
    Task.clear_all()
    User.clear_all()
    yield
    Task.clear_all()
    User.clear_all()


@pytest.fixture
def registered_user() -> User:
    """Fixture returning a pre-registered user."""
    return UserService.register_user(
        username="service_tester",
        email="service_tester@example.com",
        password="SecurePassword123!",
    )


# =============================================================================
# 1. UserService Tests
# =============================================================================

class TestUserService:
    """Unit test suite for UserService business operations."""

    def test_register_user_success(self) -> None:
        """Test successful registration through UserService."""
        user = UserService.register_user(
            username="service_bob",
            email="bob@example.com",
            password="BobPassword123!",
        )
        assert user.id is not None
        assert user.username == "service_bob"
        assert user.email == "bob@example.com"
        assert user.check_password("BobPassword123!") is True

    def test_register_user_duplicate_raises_error(self, registered_user: User) -> None:
        """Test that registering duplicate username through service raises error."""
        with pytest.raises(UserAlreadyExistsError):
            UserService.register_user(
                username=registered_user.username,
                email="new_email@example.com",
                password="SomePassword123!",
            )

    def test_authenticate_user_success_and_failure(self, registered_user: User) -> None:
        """Test user authentication logic via service layer."""
        auth_success = UserService.authenticate_user(
            username=registered_user.username,
            password="SecurePassword123!",
        )
        assert auth_success is not None
        assert auth_success.id == registered_user.id

        auth_bad_pass = UserService.authenticate_user(
            username=registered_user.username,
            password="WrongPassword!",
        )
        assert auth_bad_pass is None

        auth_unknown = UserService.authenticate_user(
            username="nonexistent",
            password="AnyPassword",
        )
        assert auth_unknown is None

    def test_get_user_queries(self, registered_user: User) -> None:
        """Test user retrieval helpers."""
        by_id = UserService.get_user_by_id(registered_user.id)
        assert by_id == registered_user

        by_username = UserService.get_user_by_username(registered_user.username)
        assert by_username == registered_user

        by_email = UserService.get_user_by_email(registered_user.email)
        assert by_email == registered_user

        # Not found cases
        assert UserService.get_user_by_id("9999") is None
        assert UserService.get_user_by_username("missing_user") is None
        assert UserService.get_user_by_email("missing@example.com") is None

    def test_list_and_delete_users(self, registered_user: User) -> None:
        """Test listing and deleting users."""
        users = UserService.list_users()
        assert len(users) == 1
        assert users[0] == registered_user

        deleted = UserService.delete_user(registered_user.id)
        assert deleted is True
        assert UserService.get_user_by_id(registered_user.id) is None
        assert len(UserService.list_users()) == 0

        # Delete non-existent
        assert UserService.delete_user("non-existent") is False


# =============================================================================
# 2. TaskService Tests
# =============================================================================

class TestTaskService:
    """Unit test suite for TaskService business operations."""

    def test_create_task_standalone(self) -> None:
        """Test creating an unassigned task."""
        task = TaskService.create_task(
            title="Deploy Service",
            description="Deploy Task Manager to production",
            status="pending",
        )
        assert task.id is not None
        assert task.title == "Deploy Service"
        assert task.description == "Deploy Task Manager to production"
        assert task.status == "pending"
        assert task.completed is False
        assert task.user_id is None

    def test_create_task_with_user(self, registered_user: User) -> None:
        """Test creating a task assigned to a valid user."""
        task = TaskService.create_task(
            title="Assigned Work",
            description="Task with user assignment",
            status="in_progress",
            user_id=registered_user.id,
        )
        assert task.user_id == registered_user.id
        assert task in registered_user.get_tasks()

    def test_create_task_validation_failure(self) -> None:
        """Test creating task with invalid title."""
        with pytest.raises(ValidationError):
            TaskService.create_task(title="")

    def test_get_task_by_id(self) -> None:
        """Test retrieving task by ID."""
        task = TaskService.create_task(title="Find Me")
        found = TaskService.get_task_by_id(task.id)
        assert found == task
        assert TaskService.get_task_by_id("fake-id") is None

    def test_list_tasks_filtering(self, registered_user: User) -> None:
        """Test listing tasks with various filtering parameters."""
        t1 = TaskService.create_task(title="T1", status="pending", user_id=registered_user.id)
        t2 = TaskService.create_task(title="T2", status="completed", user_id=registered_user.id)
        t3 = TaskService.create_task(title="T3", status="pending", user_id="other-user")

        # No filter
        assert len(TaskService.list_tasks()) == 3

        # By user
        user_tasks = TaskService.list_tasks(user_id=registered_user.id)
        assert len(user_tasks) == 2
        assert t3 not in user_tasks

        # By status
        completed_tasks = TaskService.list_tasks(status="completed")
        assert len(completed_tasks) == 1
        assert completed_tasks[0] == t2

        # Combined filter
        user_pending = TaskService.list_tasks(user_id=registered_user.id, status="pending")
        assert len(user_pending) == 1
        assert user_pending[0] == t1

    def test_update_task_success_and_not_found(self) -> None:
        """Test updating existing task fields and handling missing tasks."""
        task = TaskService.create_task(title="Old Title", status="pending")
        updated = TaskService.update_task(
            task.id,
            title="New Title",
            status="in_progress",
            description="New details",
        )
        assert updated is not None
        assert updated.title == "New Title"
        assert updated.status == "in_progress"
        assert updated.description == "New details"

        # Not found
        missing = TaskService.update_task("missing-id", title="Never Updated")
        assert missing is None

    def test_mark_task_completed(self) -> None:
        """Test mark_task_completed helper."""
        task = TaskService.create_task(title="To Complete", status="pending")
        completed = TaskService.mark_task_completed(task.id)
        assert completed is not None
        assert completed.completed is True
        assert completed.status == "completed"

        assert TaskService.mark_task_completed("missing-id") is None

    def test_delete_task(self) -> None:
        """Test deleting task through service."""
        task = TaskService.create_task(title="To Delete")
        deleted = TaskService.delete_task(task.id)
        assert deleted is True
        assert TaskService.get_task_by_id(task.id) is None
        assert TaskService.delete_task("missing-id") is False
