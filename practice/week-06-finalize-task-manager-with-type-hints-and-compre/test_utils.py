"""
test_utils.py - Pytest Unit Tests for Utility and Helper Functions.

Coverage:
- Cryptographic password hashing and verification (hash_password, verify_password).
- Input validation helpers (validate_username, validate_password_strength, validate_email_format, validate_task_status, validate_task_payload).
- HTTP request/response helpers (get_request_data, json_response, error_response).
- Custom exception hierarchy (ValidationError, AuthenticationError, UserAlreadyExistsError, NotFoundError).
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest
from flask import Flask

# Ensure current directory is in sys.path
current_dir: str = str(Path(__file__).resolve().parent)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from utils import (
        AuthenticationError,
        NotFoundError,
        UserAlreadyExistsError,
        ValidationError,
        error_response,
        get_request_data,
        hash_password,
        json_response,
        validate_email_format,
        validate_password_strength,
        validate_task_payload,
        validate_task_status,
        validate_username,
        verify_password,
    )
except ImportError:  # pragma: no cover
    from .utils import (
        AuthenticationError,
        NotFoundError,
        UserAlreadyExistsError,
        ValidationError,
        error_response,
        get_request_data,
        hash_password,
        json_response,
        validate_email_format,
        validate_password_strength,
        validate_task_payload,
        validate_task_status,
        validate_username,
        verify_password,
    )


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture
def test_app() -> Flask:
    """Create a minimal Flask application context for request/response testing."""
    app = Flask(__name__)
    return app


# =============================================================================
# 1. Password Hashing & Verification Tests
# =============================================================================

class TestPasswordUtilities:
    """Tests for cryptographic hashing and verification routines."""

    def test_hash_password_produces_salted_string(self) -> None:
        """Hash generation should produce non-empty salted string."""
        h1 = hash_password("Secret123")
        h2 = hash_password("Secret123")
        assert isinstance(h1, str)
        assert len(h1) > 20
        # Salt prevents identical plaintext producing identical hashes
        assert h1 != h2

    def test_hash_password_invalid_input(self) -> None:
        """Empty or non-string password inputs should raise ValidationError."""
        with pytest.raises(ValidationError, match="non-empty string"):
            hash_password("")

        with pytest.raises(ValidationError, match="non-empty string"):
            hash_password(None)  # type: ignore[arg-type]

    def test_verify_password_correct_and_incorrect(self) -> None:
        """verify_password returns True for matching password and False otherwise."""
        pwd = "ProductionPassword2026!"
        hashed = hash_password(pwd)

        assert verify_password(pwd, hashed) is True
        assert verify_password("WrongPassword!", hashed) is False
        assert verify_password("", hashed) is False
        assert verify_password(pwd, "") is False
        assert verify_password(None, hashed) is False  # type: ignore[arg-type]

    def test_verify_password_custom_sha256_format(self) -> None:
        """Test fallback sha256 formatted hash verification."""
        custom_hash = "sha256$deadbeef12345678$badhash"
        assert verify_password("AnyPassword", custom_hash) is False


# =============================================================================
# 2. Input Validation Tests
# =============================================================================

class TestInputValidationUtilities:
    """Tests for username, email, password strength, and status validation."""

    def test_validate_username_success(self) -> None:
        """Valid usernames pass validation and are stripped."""
        assert validate_username("john_doe") == "john_doe"
        assert validate_username("alice-99") == "alice-99"
        assert validate_username("  bob123  ") == "bob123"

    def test_validate_username_failures(self) -> None:
        """Invalid usernames raise ValidationError with helpful messages."""
        with pytest.raises(ValidationError, match="at least 3 characters"):
            validate_username("ab")

        with pytest.raises(ValidationError, match="cannot exceed 30"):
            validate_username("a" * 31)

        with pytest.raises(ValidationError, match="alphanumeric"):
            validate_username("user!name")

        with pytest.raises(ValidationError, match="valid string"):
            validate_username(None)

    def test_validate_password_strength_success(self) -> None:
        """Valid password meets length threshold."""
        assert validate_password_strength("validpass") == "validpass"
        assert validate_password_strength("longpassword", min_length=10) == "longpassword"

    def test_validate_password_strength_failures(self) -> None:
        """Short or non-string passwords raise ValidationError."""
        with pytest.raises(ValidationError, match="at least 6 characters"):
            validate_password_strength("12345")

        with pytest.raises(ValidationError, match="valid string"):
            validate_password_strength(None)

    def test_validate_email_format_success(self) -> None:
        """Valid email addresses are lowercased and stripped."""
        assert validate_email_format("USER@Domain.COM") == "user@domain.com"
        assert validate_email_format("  john.doe@test.org  ") == "john.doe@test.org"

    def test_validate_email_format_failures(self) -> None:
        """Malformed email strings raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid email address format"):
            validate_email_format("plainaddress")

        with pytest.raises(ValidationError, match="Invalid email address format"):
            validate_email_format("@missingusername.com")

        with pytest.raises(ValidationError, match="valid string"):
            validate_email_format(None)

    def test_validate_task_status_success_and_aliases(self) -> None:
        """Valid task status and common synonyms normalize correctly."""
        assert validate_task_status("pending") == "pending"
        assert validate_task_status("in_progress") == "in_progress"
        assert validate_task_status("completed") == "completed"
        assert validate_task_status("archived") == "archived"

        # Synonyms & alias normalization
        assert validate_task_status("todo") == "pending"
        assert validate_task_status("in-progress") == "in_progress"
        assert validate_task_status("doing") == "in_progress"
        assert validate_task_status("done") == "completed"
        assert validate_task_status("complete") == "completed"

    def test_validate_task_status_failures(self) -> None:
        """Invalid task status values raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid task status"):
            validate_task_status("nonexistent_state")

        with pytest.raises(ValidationError, match="must be a string"):
            validate_task_status(None)

    def test_validate_task_payload_creation(self) -> None:
        """Task payload for creation requires title and normalizes fields."""
        payload = {
            "title": "Clean Code",
            "description": "Ensure SOLID principles",
            "status": "todo",
            "user_id": 42,
            "completed": False,
        }
        validated = validate_task_payload(payload, require_title=True)
        assert validated["title"] == "Clean Code"
        assert validated["description"] == "Ensure SOLID principles"
        assert validated["status"] == "pending"
        assert validated["user_id"] == "42"
        assert validated["completed"] is False

    def test_validate_task_payload_with_name_alias(self) -> None:
        """Task payload accepting 'name' instead of 'title'."""
        validated = validate_task_payload({"name": "Task By Name"})
        assert validated["title"] == "Task By Name"

    def test_validate_task_payload_completed_sync(self) -> None:
        """Completed flag as True automatically sets status to completed."""
        validated = validate_task_payload({"title": "Done Work", "completed": True})
        assert validated["completed"] is True
        assert validated["status"] == "completed"

        # String boolean
        validated_str = validate_task_payload({"title": "Done String", "completed": "yes"})
        assert validated_str["completed"] is True
        assert validated_str["status"] == "completed"

    def test_validate_task_payload_failures(self) -> None:
        """Payload validation raises ValidationError on bad structures."""
        with pytest.raises(ValidationError, match="JSON object dictionary"):
            validate_task_payload("not a dict")

        with pytest.raises(ValidationError, match="Task title is required"):
            validate_task_payload({}, require_title=True)

        with pytest.raises(ValidationError, match="Task title cannot be empty"):
            validate_task_payload({"title": "  "}, require_title=True)


# =============================================================================
# 3. HTTP Request & Response Utilities Tests
# =============================================================================

class TestHttpUtilities:
    """Tests for Flask request parsing and JSON response formatters."""

    def test_get_request_data_json(self, test_app: Flask) -> None:
        """Extracts JSON payload when request is JSON."""
        with test_app.test_request_context(
            "/",
            method="POST",
            json={"action": "test", "value": 123},
        ):
            data = get_request_data()
            assert data == {"action": "test", "value": 123}

    def test_get_request_data_form(self, test_app: Flask) -> None:
        """Extracts form data when request is form-encoded."""
        with test_app.test_request_context(
            "/",
            method="POST",
            data={"field": "value"},
        ):
            data = get_request_data()
            assert data == {"field": "value"}

    def test_get_request_data_empty(self, test_app: Flask) -> None:
        """Returns empty dict when no payload is sent."""
        with test_app.test_request_context("/", method="GET"):
            data = get_request_data()
            assert data == {}

    def test_json_response(self, test_app: Flask) -> None:
        """Builds standard structured JSON response."""
        with test_app.app_context():
            resp, status = json_response(
                data={"item": "value"},
                status_code=201,
                message="Resource created",
            )
            assert status == 201
            assert resp.status_code == 201
            body = resp.get_json()
            assert body["success"] is True
            assert body["message"] == "Resource created"
            assert body["item"] == "value"

    def test_error_response(self, test_app: Flask) -> None:
        """Builds standard error response."""
        with test_app.app_context():
            resp, status = error_response(
                message="Bad Request Detail",
                status_code=400,
                details={"field": "title"},
            )
            assert status == 400
            assert resp.status_code == 400
            body = resp.get_json()
            assert body["success"] is False
            assert body["error"] == "Bad Request Detail"
            assert body["details"] == {"field": "title"}


# =============================================================================
# 4. Custom Exception Hierarchy Tests
# =============================================================================

class TestExceptionHierarchy:
    """Verify that domain exceptions inherit from appropriate Python standard base classes."""

    def test_validation_error_is_value_error(self) -> None:
        """ValidationError should inherit from ValueError."""
        err = ValidationError("Bad input")
        assert isinstance(err, ValueError)
        assert str(err) == "Bad input"

    def test_authentication_error_is_exception(self) -> None:
        """AuthenticationError should inherit from Exception."""
        err = AuthenticationError("Auth failed")
        assert isinstance(err, Exception)

    def test_user_already_exists_error_is_value_error(self) -> None:
        """UserAlreadyExistsError should inherit from ValueError."""
        err = UserAlreadyExistsError("User exists")
        assert isinstance(err, ValueError)

    def test_not_found_error_is_key_error(self) -> None:
        """NotFoundError should inherit from KeyError."""
        err = NotFoundError("Item not found")
        assert isinstance(err, KeyError)
