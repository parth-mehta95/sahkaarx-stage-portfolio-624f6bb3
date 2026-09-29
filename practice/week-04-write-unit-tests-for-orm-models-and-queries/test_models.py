import sys
from pathlib import Path
from datetime import date, datetime
import pytest
from sqlalchemy.exc import IntegrityError

# Ensure current module directory is on sys.path for direct pytest invocation
current_dir = str(Path(__file__).resolve().parent)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from models import (
    User,
    Task,
    create_app,
    create_task,
    create_user,
    db,
    delete_task,
    get_completed_tasks_for_user,
    get_pending_tasks_for_user,
    get_task_by_id,
    get_tasks_for_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    update_task,
)


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def app():
    """Create and configure a clean Flask application for testing."""
    test_app = create_app(database_uri="sqlite:///:memory:")
    test_app.config["TESTING"] = True
    return test_app


@pytest.fixture(scope="function")
def db_session(app):
    """Yield database session within an application context and ensure clean teardown."""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="function")
def sample_user(db_session):
    """Fixture providing a persisted User instance."""
    user = User(
        username="alice",
        email="alice@example.com",
        password="securepassword123",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture(scope="function")
def another_user(db_session):
    """Fixture providing a second persisted User instance for isolation testing."""
    user = User(
        username="bob",
        email="bob@example.com",
        password="anotherpassword456",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture(scope="function")
def sample_task(db_session, sample_user):
    """Fixture providing a persisted Task associated with sample_user."""
    task = Task(
        title="Complete project documentation",
        description="Write comprehensive docstrings and README",
        due_date="2026-10-15",
        status="pending",
        completed=False,
        user_id=sample_user.id,
    )
    db_session.add(task)
    db_session.commit()
    return task


@pytest.fixture(scope="function")
def multiple_tasks(db_session, sample_user, another_user):
    """Fixture providing multiple tasks for user filtering and isolation tests."""
    tasks = [
        Task(
            title="Alice Task 1",
            description="First task for Alice",
            status="pending",
            completed=False,
            user_id=sample_user.id,
        ),
        Task(
            title="Alice Task 2",
            description="Second task for Alice",
            status="completed",
            completed=True,
            user_id=sample_user.id,
        ),
        Task(
            title="Alice Task 3",
            description="Third task for Alice",
            status="in_progress",
            completed=False,
            user_id=sample_user.id,
        ),
        Task(
            title="Bob Task 1",
            description="Task belonging exclusively to Bob",
            status="pending",
            completed=False,
            user_id=another_user.id,
        ),
    ]
    db_session.add_all(tasks)
    db_session.commit()
    return tasks


# ============================================================================
# User Model Unit Tests
# ============================================================================

def test_user_creation_and_attributes(db_session):
    """Verify user creation, property assignment, and password hashing."""
    user = User(username="charlie", email="charlie@example.com", password="password789")
    db_session.add(user)
    db_session.commit()

    assert user.id is not None
    assert user.username == "charlie"
    assert user.email == "charlie@example.com"
    assert user.password_hash != "password789"
    assert user.check_password("password789") is True
    assert user.check_password("wrongpassword") is False
    assert isinstance(user.created_at, datetime)


def test_user_validation_errors():
    """Verify User model validation handles empty or invalid inputs."""
    with pytest.raises(ValueError, match="Username cannot be empty"):
        User(username="   ", email="valid@example.com")

    with pytest.raises(TypeError, match="Username must be a string"):
        User(username=123, email="valid@example.com")

    with pytest.raises(ValueError, match="Email must be a valid non-empty email address"):
        User(username="testuser", email="invalid-email")

    with pytest.raises(TypeError, match="Email must be a string"):
        User(username="testuser", email=None)

    with pytest.raises(ValueError, match="Password cannot be empty"):
        User(username="testuser", email="test@example.com", password="")


def test_user_representation_and_dict(sample_user):
    """Verify User string representation and dictionary serialization."""
    assert repr(sample_user) == f"<User {sample_user.username}>"

    data = sample_user.to_dict()
    assert data["id"] == sample_user.id
    assert data["username"] == "alice"
    assert data["email"] == "alice@example.com"
    assert "password_hash" not in data
    assert "task_count" in data


def test_user_unique_constraints(db_session, sample_user):
    """Verify that duplicate username or email raises an IntegrityError."""
    # Duplicate username
    duplicate_username_user = User(
        username=sample_user.username,
        email="unique1@example.com",
        password="pass",
    )
    db_session.add(duplicate_username_user)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Duplicate email
    duplicate_email_user = User(
        username="unique_user_2",
        email=sample_user.email,
        password="pass",
    )
    db_session.add(duplicate_email_user)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ============================================================================
# Task Model Unit Tests
# ============================================================================

def test_task_creation_and_attributes(db_session, sample_user):
    """Verify task creation with proper attributes and default values."""
    task = Task(
        title="Setup CI pipeline",
        description="Configure GitHub Actions",
        due_date=date(2026, 11, 1),
        user_id=sample_user.id,
    )
    db_session.add(task)
    db_session.commit()

    assert task.id is not None
    assert task.title == "Setup CI pipeline"
    assert task.description == "Configure GitHub Actions"
    assert task.due_date == date(2026, 11, 1)
    assert task.status == "pending"
    assert task.completed is False
    assert task.user_id == sample_user.id
    assert isinstance(task.created_at, datetime)


def test_task_validation_errors(sample_user):
    """Verify Task model validation for invalid fields."""
    with pytest.raises(ValueError, match="Title cannot be empty"):
        Task(title="   ", user_id=sample_user.id)

    with pytest.raises(TypeError, match="Title must be a string"):
        Task(title=12345, user_id=sample_user.id)

    with pytest.raises(ValueError, match="Invalid status"):
        Task(title="Valid Title", status="unknown_status", user_id=sample_user.id)

    with pytest.raises(TypeError, match="User ID must be an integer"):
        Task(title="Valid Title", user_id="123")

    with pytest.raises(ValueError, match="User ID must be a positive integer"):
        Task(title="Valid Title", user_id=0)


def test_task_update_and_mark_completed(db_session, sample_task):
    """Verify Task update method and mark_completed method."""
    sample_task.update(
        title="Updated Documentation Title",
        status="in_progress",
    )
    db_session.commit()
    assert sample_task.title == "Updated Documentation Title"
    assert sample_task.status == "in_progress"

    sample_task.mark_completed()
    db_session.commit()
    assert sample_task.completed is True
    assert sample_task.status == "completed"


def test_task_representation_and_dict(sample_task):
    """Verify Task string representation and serialization."""
    assert repr(sample_task) == f"<Task {sample_task.id}: {sample_task.title}>"

    data = sample_task.to_dict()
    assert data["id"] == sample_task.id
    assert data["title"] == sample_task.title
    assert data["user_id"] == sample_task.user_id
    assert data["status"] == "pending"
    assert data["completed"] is False


# ============================================================================
# Relationship & Foreign Key Constraints Unit Tests
# ============================================================================

def test_user_task_bidirectional_relationship(db_session, sample_user):
    """Verify bidirectional 1-to-many relationship between User and Task."""
    task1 = Task(title="Task One", user_id=sample_user.id)
    task2 = Task(title="Task Two", user_id=sample_user.id)
    db_session.add_all([task1, task2])
    db_session.commit()

    # User -> Tasks
    assert len(sample_user.tasks) == 2
    assert task1 in sample_user.tasks
    assert task2 in sample_user.tasks

    # Task -> User (backref)
    assert task1.user == sample_user
    assert task2.user == sample_user
    assert task1.user.username == "alice"


def test_foreign_key_constraint_invalid_user_id(db_session):
    """Verify that foreign key enforcement rejects tasks with non-existent user IDs."""
    invalid_task = Task(title="Orphan Task with non-existent user", user_id=99999)
    db_session.add(invalid_task)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cascade_delete_removes_tasks(db_session, sample_user):
    """Verify that deleting a User cascades and deletes all associated Tasks."""
    task1 = Task(title="Dependent Task 1", user_id=sample_user.id)
    task2 = Task(title="Dependent Task 2", user_id=sample_user.id)
    db_session.add_all([task1, task2])
    db_session.commit()

    task1_id = task1.id
    task2_id = task2.id

    # Delete the parent user
    db_session.delete(sample_user)
    db_session.commit()

    # Verify user is deleted
    assert db.session.get(User, sample_user.id) is None

    # Verify both child tasks are cascade-deleted
    assert db.session.get(Task, task1_id) is None
    assert db.session.get(Task, task2_id) is None


def test_delete_task_does_not_delete_user(db_session, sample_user, sample_task):
    """Verify that deleting a task does not delete the parent user."""
    user_id = sample_user.id
    db_session.delete(sample_task)
    db_session.commit()

    assert db.session.get(Task, sample_task.id) is None
    assert db.session.get(User, user_id) is not None


# ============================================================================
# Database Query Functions Unit Tests
# ============================================================================

def test_query_create_and_get_user(db_session):
    """Verify create_user, get_user_by_id, get_user_by_username, and get_user_by_email."""
    user = create_user(
        username="david",
        email="david@example.com",
        password="davidpassword",
    )
    assert user.id is not None

    # Test retrieval by ID
    retrieved_by_id = get_user_by_id(user.id)
    assert retrieved_by_id is not None
    assert retrieved_by_id.username == "david"

    # Test retrieval by username
    retrieved_by_username = get_user_by_username("david")
    assert retrieved_by_username is not None
    assert retrieved_by_username.id == user.id

    # Test retrieval by email
    retrieved_by_email = get_user_by_email("david@example.com")
    assert retrieved_by_email is not None
    assert retrieved_by_email.id == user.id

    # Test non-existent user returns None
    assert get_user_by_id(999999) is None
    assert get_user_by_username("nonexistent") is None


def test_query_create_and_get_task(db_session, sample_user):
    """Verify create_task and get_task_by_id query functions."""
    task = create_task(
        title="Query Task",
        user_id=sample_user.id,
        description="Testing task queries",
        status="pending",
    )
    assert task.id is not None

    retrieved_task = get_task_by_id(task.id)
    assert retrieved_task is not None
    assert retrieved_task.title == "Query Task"
    assert retrieved_task.user_id == sample_user.id

    # Test non-existent task returns None
    assert get_task_by_id(888888) is None


def test_query_get_tasks_for_user_and_isolation(db_session, sample_user, another_user, multiple_tasks):
    """Verify get_tasks_for_user retrieves only tasks for that specific user."""
    alice_tasks = get_tasks_for_user(sample_user.id)
    bob_tasks = get_tasks_for_user(another_user.id)

    assert len(alice_tasks) == 3
    assert len(bob_tasks) == 1

    # Verify task ownership isolation
    for task in alice_tasks:
        assert task.user_id == sample_user.id
        assert task.title != "Bob Task 1"

    for task in bob_tasks:
        assert task.user_id == another_user.id
        assert task.title == "Bob Task 1"


def test_query_get_tasks_for_user_filters(db_session, sample_user, multiple_tasks):
    """Verify get_tasks_for_user with status and completion filters."""
    # Filter by status="completed"
    completed_tasks = get_tasks_for_user(sample_user.id, status="completed")
    assert len(completed_tasks) == 1
    assert completed_tasks[0].title == "Alice Task 2"

    # Filter by completed=True helper
    helper_completed = get_completed_tasks_for_user(sample_user.id)
    assert len(helper_completed) == 1
    assert helper_completed[0].completed is True

    # Filter by pending helper
    pending_tasks = get_pending_tasks_for_user(sample_user.id)
    assert len(pending_tasks) == 1
    assert pending_tasks[0].title == "Alice Task 1"
    assert pending_tasks[0].status == "pending"


def test_query_update_and_delete_task(db_session, sample_user):
    """Verify update_task and delete_task query functions."""
    task = create_task(
        title="Original Title",
        user_id=sample_user.id,
        status="pending",
    )

    # Update task
    updated = update_task(task.id, title="Modified Title", status="completed", completed=True)
    assert updated is not None
    assert updated.title == "Modified Title"
    assert updated.status == "completed"
    assert updated.completed is True

    # Confirm persistence
    fetched = get_task_by_id(task.id)
    assert fetched.title == "Modified Title"

    # Delete task
    result = delete_task(task.id)
    assert result is True
    assert get_task_by_id(task.id) is None

    # Deleting non-existent task returns False
    assert delete_task(999999) is False
    assert update_task(999999, title="Nothing") is None


def test_query_empty_results_for_user_without_tasks(db_session):
    """Verify query functions handle users with no tasks gracefully."""
    fresh_user = create_user(username="emily", email="emily@example.com", password="pwd")
    tasks = get_tasks_for_user(fresh_user.id)
    assert tasks == []
    assert get_completed_tasks_for_user(fresh_user.id) == []
    assert get_pending_tasks_for_user(fresh_user.id) == []


# ============================================================================
# Main Entrypoint for Direct Execution
# ============================================================================

if __name__ == "__main__":
    import sys
    print("Running pytest on test_models.py...")
    sys.exit(pytest.main(["-v", __file__]))
