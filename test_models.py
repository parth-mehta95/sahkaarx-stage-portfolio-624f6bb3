"""test_models.py - Unit tests verifying type hints, type safety, and input validation constraints for Task Manager models."""
from datetime import date, datetime
import inspect
from typing import get_type_hints, Optional, Union
import pytest
from app import create_app
from models import db, Task, User


# ==========================================================
# Fixtures
# ==========================================================


@pytest.fixture
def app():
    """Create test application context using an in-memory SQLite database."""
    test_app = create_app(database_uri="sqlite:///:memory:")
    test_app.config["TESTING"] = True

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


# ==========================================================
# 1. Type Hint Enforcement & Signature Tests
# ==========================================================


def test_task_init_type_hints():
    """Verify Task.__init__ has accurate type hints for all parameters and return value."""
    hints = get_type_hints(Task.__init__)
    assert "return" in hints
    assert hints["return"] is type(None)
    assert hints["title"] is str
    assert hints["description"] == Optional[str]
    assert hints["due_date"] == Optional[Union[date, datetime, str]]
    assert hints["status"] is str
    assert hints["completed"] is bool
    assert hints["user_id"] == Optional[int]


def test_task_all_methods_have_type_hints():
    """Verify all Task public and helper methods enforce type hints on arguments and returns."""
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
        for param_name in sig.parameters:
            if param_name in ("self", "cls"):
                continue
            assert param_name in hints, f"Missing type hint for '{param_name}' in {method.__name__}"


def test_user_methods_have_type_hints():
    """Verify all User methods enforce type hints on arguments and returns."""
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
        for param_name in sig.parameters:
            if param_name in ("self", "cls"):
                continue
            assert param_name in hints, f"Missing type hint for '{param_name}' in {method.__name__}"


# ==========================================================
# 2. Valid Task Creation Tests (Correct Types & Constraints)
# ==========================================================


def test_valid_task_creation_minimal():
    """Verify Task creation with only mandatory title argument."""
    task = Task(title="Buy groceries")
    assert task.title == "Buy groceries"
    assert task.description == ""
    assert task.due_date is None
    assert task.status == "pending"
    assert task.completed is False
    assert task.user_id is None

    # Check runtime types
    assert isinstance(task.title, str)
    assert isinstance(task.status, str)
    assert isinstance(task.completed, bool)


def test_valid_task_creation_full_parameters():
    """Verify Task creation with all parameters specified with exact types."""
    task = Task(
        title="Complete Assignment",
        description="Write unit tests for models and routes",
        due_date=date(2026, 10, 15),
        status="in-progress",
        completed=False,
        user_id=1,
    )
    assert task.title == "Complete Assignment"
    assert task.description == "Write unit tests for models and routes"
    assert task.due_date == date(2026, 10, 15)
    assert task.status == "in-progress"
    assert task.completed is False
    assert task.user_id == 1


def test_valid_task_creation_date_formats():
    """Verify Task._parse_date supports date objects, datetime objects, and ISO date strings."""
    # Date object
    task_date = Task(title="Task 1", due_date=date(2026, 11, 20))
    assert task_date.due_date == date(2026, 11, 20)
    assert isinstance(task_date.due_date, date)

    # Datetime object
    task_dt = Task(title="Task 2", due_date=datetime(2026, 11, 20, 15, 30))
    assert task_dt.due_date == date(2026, 11, 20)

    # String YYYY-MM-DD
    task_str = Task(title="Task 3", due_date="2026-11-20")
    assert task_str.due_date == date(2026, 11, 20)

    # None
    task_none = Task(title="Task 4", due_date=None)
    assert task_none.due_date is None


def test_valid_task_trims_whitespace():
    """Verify string fields are stripped of leading and trailing whitespace."""
    task = Task(
        title="   Refactor architecture   ",
        description="   Clean code principles   ",
        status="   in-progress   ",
    )
    assert task.title == "Refactor architecture"
    assert task.description == "Clean code principles"
    assert task.status == "in-progress"


def test_valid_task_completed_boolean():
    """Verify boolean completed flag is properly set and stored."""
    task_active = Task(title="Active task", completed=False)
    assert task_active.completed is False

    task_done = Task(title="Done task", completed=True, status="completed")
    assert task_done.completed is True


def test_valid_task_mark_completed():
    """Verify mark_completed updates completed to True and status to 'completed'."""
    task = Task(title="Finish docs", status="pending", completed=False)
    task.mark_completed()
    assert task.completed is True
    assert task.status == "completed"


def test_valid_task_update():
    """Verify Task.update modifies attributes with correct types and parses dates."""
    task = Task(title="Initial Title", description="Initial description")
    task.update(
        title="Updated Title",
        description="Updated description",
        due_date="2026-12-01",
        status="completed",
        completed=True,
    )
    assert task.title == "Updated Title"
    assert task.description == "Updated description"
    assert task.due_date == date(2026, 12, 1)
    assert task.status == "completed"
    assert task.completed is True


def test_valid_task_update_completed_sets_status():
    """Verify updating completed=True automatically updates status to 'completed'."""
    task = Task(title="Pending task")
    task.update(completed=True)
    assert task.completed is True
    assert task.status == "completed"


def test_valid_task_to_dict():
    """Verify Task.to_dict produces dictionary with expected keys and types."""
    task = Task(
        title="Dict Task",
        description="Description text",
        due_date="2026-10-31",
        status="pending",
        completed=False,
        user_id=42,
    )
    task_dict = task.to_dict()
    assert isinstance(task_dict, dict)
    assert task_dict["title"] == "Dict Task"
    assert task_dict["description"] == "Description text"
    assert task_dict["due_date"] == "2026-10-31"
    assert task_dict["status"] == "pending"
    assert task_dict["completed"] is False
    assert task_dict["user_id"] == 42
    assert "id" in task_dict


def test_valid_task_repr():
    """Verify Task.__repr__ formatting."""
    task = Task(title="Test Repr")
    assert repr(task) == "<Task None: Test Repr>"


# ==========================================================
# 3. Invalid Task Input Rejection Tests
# ==========================================================


@pytest.mark.parametrize(
    "empty_title",
    ["", "   ", "\t", "\n", "  \r\n  "],
)
def test_task_creation_rejects_empty_title(empty_title):
    """Verify Task rejects empty or whitespace-only title with ValueError."""
    with pytest.raises(ValueError, match="Title cannot be empty"):
        Task(title=empty_title)


@pytest.mark.parametrize(
    "wrong_title",
    [123, 45.67, None, True, False, ["Task Title"], {"title": "Task Title"}],
)
def test_task_creation_rejects_wrong_title_type(wrong_title):
    """Verify Task rejects non-string title with TypeError."""
    with pytest.raises(TypeError, match="Title must be a string"):
        Task(title=wrong_title)


@pytest.mark.parametrize(
    "wrong_description",
    [123, 45.67, True, False, ["Description"], {"desc": "Description"}],
)
def test_task_creation_rejects_wrong_description_type(wrong_description):
    """Verify Task rejects non-string description with TypeError."""
    with pytest.raises(TypeError, match="Description must be a string"):
        Task(title="Valid Title", description=wrong_description)


@pytest.mark.parametrize(
    "empty_status",
    ["", "   ", "\t"],
)
def test_task_creation_rejects_empty_status(empty_status):
    """Verify Task rejects empty or whitespace-only status with ValueError."""
    with pytest.raises(ValueError, match="Status cannot be empty"):
        Task(title="Valid Title", status=empty_status)


@pytest.mark.parametrize(
    "wrong_status",
    [123, None, True, False, ["pending"], {"status": "pending"}],
)
def test_task_creation_rejects_wrong_status_type(wrong_status):
    """Verify Task rejects non-string status with TypeError."""
    with pytest.raises(TypeError, match="Status must be a string"):
        Task(title="Valid Title", status=wrong_status)


@pytest.mark.parametrize(
    "wrong_completed",
    ["true", "false", 1, 0, None, [True], {"completed": True}],
)
def test_task_creation_rejects_wrong_completed_type(wrong_completed):
    """Verify Task rejects non-boolean completed flag with TypeError."""
    with pytest.raises(TypeError, match="Completed must be a boolean"):
        Task(title="Valid Title", completed=wrong_completed)


@pytest.mark.parametrize(
    "wrong_user_id_type",
    ["1", "user-1", 3.14, True, False, [1], {"id": 1}],
)
def test_task_creation_rejects_wrong_user_id_type(wrong_user_id_type):
    """Verify Task rejects non-integer or boolean user_id with TypeError."""
    with pytest.raises(TypeError, match="User ID must be an integer"):
        Task(title="Valid Title", user_id=wrong_user_id_type)


@pytest.mark.parametrize(
    "invalid_user_id_val",
    [0, -1, -100],
)
def test_task_creation_rejects_non_positive_user_id(invalid_user_id_val):
    """Verify Task rejects zero or negative user_id with ValueError."""
    with pytest.raises(ValueError, match="User ID must be a positive integer"):
        Task(title="Valid Title", user_id=invalid_user_id_val)


@pytest.mark.parametrize(
    "malformed_date",
    [
        "not-a-date",
        "12-31-2026",
        "2026/12/31",
        "2026-02-30",
        "2026-13-01",
        "2026-00-10",
        "invalid",
    ],
)
def test_task_creation_rejects_malformed_due_date_string(malformed_date):
    """Verify Task rejects invalid date string format with ValueError."""
    with pytest.raises(ValueError):
        Task(title="Valid Title", due_date=malformed_date)


@pytest.mark.parametrize(
    "wrong_due_date_type",
    [20261015, True, False, ["2026-10-15"], {"due_date": "2026-10-15"}],
)
def test_task_creation_rejects_wrong_due_date_type(wrong_due_date_type):
    """Verify Task rejects non-date/string/datetime due_date types with ValueError."""
    with pytest.raises(ValueError, match="Unsupported date format"):
        Task(title="Valid Title", due_date=wrong_due_date_type)


# ==========================================================
# 4. Invalid Task Update Rejection Tests
# ==========================================================


def test_task_update_rejects_empty_title():
    """Verify Task.update rejects empty or whitespace title with ValueError."""
    task = Task(title="Original Title")
    with pytest.raises(ValueError, match="Title cannot be empty"):
        task.update(title="")
    with pytest.raises(ValueError, match="Title cannot be empty"):
        task.update(title="   ")


def test_task_update_rejects_wrong_title_type():
    """Verify Task.update rejects non-string title with TypeError."""
    task = Task(title="Original Title")
    with pytest.raises(TypeError, match="Title must be a string"):
        task.update(title=123)


def test_task_update_rejects_wrong_description_type():
    """Verify Task.update rejects non-string description with TypeError."""
    task = Task(title="Original Title")
    with pytest.raises(TypeError, match="Description must be a string"):
        task.update(description=12345)


def test_task_update_rejects_empty_status():
    """Verify Task.update rejects empty status with ValueError."""
    task = Task(title="Original Title")
    with pytest.raises(ValueError, match="Status cannot be empty"):
        task.update(status="")


def test_task_update_rejects_wrong_status_type():
    """Verify Task.update rejects non-string status with TypeError."""
    task = Task(title="Original Title")
    with pytest.raises(TypeError, match="Status must be a string"):
        task.update(status=100)


def test_task_update_rejects_wrong_completed_type():
    """Verify Task.update rejects non-boolean completed flag with TypeError."""
    task = Task(title="Original Title")
    with pytest.raises(TypeError, match="Completed must be a boolean"):
        task.update(completed="yes")


def test_task_update_rejects_invalid_due_date():
    """Verify Task.update rejects invalid due_date formats or types."""
    task = Task(title="Original Title")
    with pytest.raises(ValueError):
        task.update(due_date="invalid-date")
    with pytest.raises(ValueError, match="Unsupported date format"):
        task.update(due_date=99999)


# ==========================================================
# 5. User Model Validation & Authentication Tests
# ==========================================================


def test_user_creation_valid():
    """Verify User creation with valid types and password hashing."""
    user = User(username="alice", email="alice@example.com", password="securepassword123")
    assert user.username == "alice"
    assert user.email == "alice@example.com"
    assert user.check_password("securepassword123") is True
    assert user.check_password("wrongpassword") is False
    assert user.to_dict() == {"id": None, "username": "alice", "email": "alice@example.com"}
    assert repr(user) == "<User alice>"

    user_no_pwd = User(username="nopass", email="nopass@example.com")
    assert user_no_pwd.check_password("any") is False


@pytest.mark.parametrize("empty_user", ["", "   "])
def test_user_creation_rejects_empty_username(empty_user):
    """Verify User creation rejects empty username."""
    with pytest.raises(ValueError, match="Username cannot be empty"):
        User(username=empty_user, email="test@example.com")


@pytest.mark.parametrize("wrong_user_type", [123, True, ["user"]])
def test_user_creation_rejects_wrong_username_type(wrong_user_type):
    """Verify User creation rejects non-string username."""
    with pytest.raises(TypeError, match="Username must be a string"):
        User(username=wrong_user_type, email="test@example.com")


@pytest.mark.parametrize("bad_email", ["", "   ", "invalid-email-no-at"])
def test_user_creation_rejects_invalid_email(bad_email):
    """Verify User creation rejects invalid email."""
    with pytest.raises(ValueError, match="Email must be a valid non-empty email address"):
        User(username="testuser", email=bad_email)


@pytest.mark.parametrize("wrong_email_type", [123, True, ["email@example.com"]])
def test_user_creation_rejects_wrong_email_type(wrong_email_type):
    """Verify User creation rejects non-string email."""
    with pytest.raises(TypeError, match="Email must be a string"):
        User(username="testuser", email=wrong_email_type)


def test_user_creation_rejects_wrong_password_type():
    """Verify User creation rejects non-string password."""
    with pytest.raises(TypeError, match="Password must be a string"):
        User(username="testuser", email="test@example.com", password=123456)


def test_user_creation_rejects_empty_password():
    """Verify User creation rejects empty password."""
    with pytest.raises(ValueError, match="Password cannot be empty"):
        User(username="testuser", email="test@example.com", password="")


# ==========================================================
# 6. Database Persistence & ORM Integration Tests
# ==========================================================


def test_task_database_persistence_and_relationship(app):
    """Verify persisting valid User and Task instances in database and relationship integrity."""
    with app.app_context():
        user = User.register(username="dave", email="dave@example.com", password="password")
        assert user.id is not None

        task = Task(
            title="Database Integration Task",
            description="Ensure ORM models map to SQLite properly",
            due_date="2026-11-15",
            status="pending",
            completed=False,
            user_id=user.id,
        )
        db.session.add(task)
        db.session.commit()

        # Query back
        retrieved_task = db.session.get(Task, task.id)
        assert retrieved_task is not None
        assert retrieved_task.title == "Database Integration Task"
        assert retrieved_task.due_date == date(2026, 11, 15)
        assert retrieved_task.user_id == user.id
        assert retrieved_task.user == user

        # Verify user tasks relationship
        tasks = user.get_tasks()
        assert len(tasks) == 1
        assert tasks[0].id == task.id


def test_user_authenticate_and_registration(app):
    """Verify User.register and User.authenticate logic and persistence."""
    with app.app_context():
        user = User.register(username="authuser", email="auth@example.com", password="secretpassword")
        assert user.id is not None
        assert user.check_password("secretpassword") is True
        assert user.check_password("wrong") is False

        # Authenticate success
        auth_user = User.authenticate("authuser", "secretpassword")
        assert auth_user is not None
        assert auth_user.id == user.id

        # Authenticate wrong password
        assert User.authenticate("authuser", "wrongpassword") is None

        # Authenticate non-existent user
        assert User.authenticate("nonexistent", "secretpassword") is None

