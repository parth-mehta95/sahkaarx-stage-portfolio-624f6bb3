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
current_dir = str(Path(__file__).resolve().parent)
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
def test_app():
    """Create a minimal Flask application context for request/response helpers."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


# =============================================================================
# 1. Password Hashing & Verification Tests
# =============================================================================

class TestPasswordUtilities:
    """Verify cryptographic password hashing and constant-time verification."""

    def test_hash_password_success(self):
        """hash_password returns salted hash different from plaintext."""
        pwd = "SecretPassword123!"
        hashed = hash_password(pwd)
        assert hashed != pwd
        assert isinstance(hashed, str)
        assert len(hashed) > 10

    def test_hash_password_unique_salts(self):
        """Hashing the same password multiple times produces distinct salted hashes."""
        pwd = "SecretPassword123!"
        h1 = hash_password(pwd)
        h2 = hash_password(pwd)
        assert h1 != h2

    def test_hash_password_invalid_inputs(self):
        """hash_password raises ValidationError on empty or non-string password."""
        with pytest.raises(ValidationError, match="non-empty string"):
            hash_password("")

        with pytest.raises(ValidationError, match="non-empty string"):
            hash_password(None)  # type: ignore

    def test_verify_password_match(self):
        """verify_password returns True for matching plaintext and hash."""
        pwd = "CorrectHorseBatteryStaple!"
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed) is True

    def test_verify_password_mismatch(self):
        """verify_password returns False for wrong password."""
        pwd = "CorrectPassword123"
        hashed = hash_password(pwd)
        assert verify_password("WrongPassword456", hashed) is False

    def test_verify_password_invalid_inputs(self):
        """verify_password returns False safely for invalid/empty inputs without raising."""
        hashed = hash_password("ValidPassword123")
        assert verify_password("", hashed) is False
        assert verify_password(None, hashed) is False  # type: ignore
        assert verify_password("ValidPassword123", "") is False
        assert verify_password("ValidPassword123", None) is False  # type: ignore


# =============================================================================
# 2. Input Validation Helper Tests
# =============================================================================

class TestValidationHelpers:
    """Verify username, password, email, status, and payload validators."""

    def test_validate_username_valid(self):
        """validate_username accepts clean alphanumeric, hyphen, period, and underscore names."""
        assert validate_username("john_doe") == "john_doe"
        assert validate_username("  jane.doe-99  ") == "jane.doe-99"

    def test_validate_username_invalid_types_and_empty(self):
        """validate_username raises ValidationError for non-string, empty, or whitespace."""
        with pytest.raises(ValidationError, match="valid non-empty string"):
            validate_username(None)

        with pytest.raises(ValidationError, match="valid non-empty string"):
            validate_username(12345)

        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_username("")

        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_username("   ")

    def test_validate_username_length_boundaries(self):
        """validate_username enforces length between 3 and 50 characters."""
        with pytest.raises(ValidationError, match="at least 3 characters"):
            validate_username("ab")

        long_name = "a" * 51
        with pytest.raises(ValidationError, match="must not exceed 50 characters"):
            validate_username(long_name)

        # Exact boundary tests
        assert len(validate_username("abc")) == 3
        assert len(validate_username("a" * 50)) == 50

    def test_validate_username_disallowed_characters(self):
        """validate_username rejects names with spaces or illegal characters."""
        with pytest.raises(ValidationError, match="alphanumeric characters"):
            validate_username("user@name")

        with pytest.raises(ValidationError, match="alphanumeric characters"):
            validate_username("user name")

    def test_validate_password_strength_valid(self):
        """validate_password_strength returns password if length requirement is met."""
        assert validate_password_strength("validpass") == "validpass"
        assert validate_password_strength("123456", min_length=6) == "123456"

    def test_validate_password_strength_invalid(self):
        """validate_password_strength raises ValidationError for non-string or short passwords."""
        with pytest.raises(ValidationError, match="must be a string"):
            validate_password_strength(None)

        with pytest.raises(ValidationError, match="at least 6 characters"):
            validate_password_strength("12345")

        with pytest.raises(ValidationError, match="at least 8 characters"):
            validate_password_strength("1234567", min_length=8)

    def test_validate_email_format_valid(self):
        """validate_email_format normalizes valid emails."""
        assert validate_email_format("  Alice@Example.COM  ") == "alice@example.com"
        assert validate_email_format("") == ""
        assert validate_email_format(None) == ""

    def test_validate_email_format_invalid(self):
        """validate_email_format raises ValidationError for malformed non-empty emails."""
        with pytest.raises(ValidationError, match="must be a string"):
            validate_email_format(123)

        with pytest.raises(ValidationError, match="Invalid email address format"):
            validate_email_format("not-an-email")

        with pytest.raises(ValidationError, match="Invalid email address format"):
            validate_email_format("missing@domain")

    def test_validate_task_status_canonical(self):
        """validate_task_status accepts canonical statuses."""
        assert validate_task_status("pending") == "pending"
        assert validate_task_status("in_progress") == "in_progress"
        assert validate_task_status("completed") == "completed"

    def test_validate_task_status_aliases(self):
        """validate_task_status normalizes known status aliases."""
        assert validate_task_status("done") == "completed"
        assert validate_task_status("finished") == "completed"
        assert validate_task_status("doing") == "in_progress"
        assert validate_task_status("active") == "in_progress"
        assert validate_task_status("todo") == "pending"
        assert validate_task_status("open") == "pending"
        assert validate_task_status(None) == "pending"
        assert validate_task_status("") == "pending"

    def test_validate_task_status_invalid(self):
        """validate_task_status raises ValidationError for unknown status values."""
        with pytest.raises(ValidationError, match="Invalid status"):
            validate_task_status("cancelled")

    def test_validate_task_payload_valid(self):
        """validate_task_payload validates and sanitizes raw dictionary input."""
        raw = {
            "title": "  Sanitize Database  ",
            "description": "  Clean orphan rows  ",
            "status": "doing",
            "user_id": 42,
        }
        cleaned = validate_task_payload(raw)
        assert cleaned["title"] == "Sanitize Database"
        assert cleaned["description"] == "Clean orphan rows"
        assert cleaned["status"] == "in_progress"
        assert cleaned["user_id"] == "42"

    def test_validate_task_payload_name_alias(self):
        """validate_task_payload accepts 'name' as an alias for 'title'."""
        cleaned = validate_task_payload({"name": "Task from name field"})
        assert cleaned["title"] == "Task from name field"

    def test_validate_task_payload_missing_title(self):
        """validate_task_payload raises ValidationError when title is missing or empty."""
        with pytest.raises(ValidationError, match="Task title is required"):
            validate_task_payload({}, require_title=True)

        with pytest.raises(ValidationError, match="Task title is required"):
            validate_task_payload({"title": "   "}, require_title=True)

    def test_validate_task_payload_optional_title(self):
        """validate_task_payload allows omitting title when require_title=False."""
        cleaned = validate_task_payload({"status": "completed"}, require_title=False)
        assert "title" not in cleaned
        assert cleaned["status"] == "completed"

    def test_validate_task_payload_non_dict(self):
        """validate_task_payload raises ValidationError for non-dict payloads."""
        with pytest.raises(ValidationError, match="must be a JSON object"):
            validate_task_payload("string payload")  # type: ignore


# =============================================================================
# 3. HTTP Request & Response Helper Tests
# =============================================================================

class TestHttpHelpers:
    """Verify get_request_data, json_response, and error_response formatting."""

    def test_get_request_data_json(self, test_app: Flask):
        """get_request_data parses application/json body correctly."""
        with test_app.test_request_context("/", method="POST", json={"key": "value"}):
            data = get_request_data()
            assert data == {"key": "value"}

    def test_get_request_data_form(self, test_app: Flask):
        """get_request_data parses form data correctly."""
        with test_app.test_request_context("/", method="POST", data={"form_key": "form_value"}):
            data = get_request_data()
            assert data == {"form_key": "form_value"}

    def test_get_request_data_empty(self, test_app: Flask):
        """get_request_data returns empty dict when no body is provided."""
        with test_app.test_request_context("/", method="GET"):
            data = get_request_data()
            assert data == {}

    def test_json_response_defaults(self, test_app: Flask):
        """json_response defaults to status_code 200."""
        with test_app.test_request_context("/"):
            response, code = json_response({"result": "success"})
            assert code == 200
            assert response.status_code == 200
            assert response.is_json
            data = response.get_json()
            assert data["status_code"] == 200
            assert data["result"] == "success"

    def test_json_response_with_message_and_primitive_data(self, test_app: Flask):
        """json_response wraps primitive data under 'data' and adds message."""
        with test_app.test_request_context("/"):
            response, code = json_response("plain string data", status_code=201, message="Created OK")
            assert code == 201
            data = response.get_json()
            assert data["status_code"] == 201
            assert data["message"] == "Created OK"
            assert data["data"] == "plain string data"

    def test_error_response_defaults(self, test_app: Flask):
        """error_response defaults to status_code 400 and returns JSON error object."""
        with test_app.test_request_context("/"):
            response, code = error_response("Bad Request Occurred")
            assert code == 400
            assert response.status_code == 400
            data = response.get_json()
            assert data["status_code"] == 400
            assert data["error"] == "Bad Request Occurred"

    def test_error_response_custom_code(self, test_app: Flask):
        """error_response supports custom HTTP error codes (e.g. 404, 409)."""
        with test_app.test_request_context("/"):
            response, code = error_response("Not Found", status_code=404, extra_detail="detail")
            assert code == 404
            data = response.get_json()
            assert data["status_code"] == 404
            assert data["error"] == "Not Found"
            assert data["extra_detail"] == "detail"


# =============================================================================
# 4. Custom Exception Class Hierarchy Tests
# =============================================================================

class TestExceptionHierarchy:
    """Verify custom exception inheritance relationships."""

    def test_validation_error_is_value_error(self):
        """ValidationError is a subclass of ValueError."""
        assert issubclass(ValidationError, ValueError)
        err = ValidationError("invalid")
        assert isinstance(err, ValueError)

    def test_user_already_exists_error_is_value_error(self):
        """UserAlreadyExistsError is a subclass of ValueError."""
        assert issubclass(UserAlreadyExistsError, ValueError)

    def test_not_found_error_is_key_error(self):
        """NotFoundError is a subclass of KeyError."""
        assert issubclass(NotFoundError, KeyError)

    def test_authentication_error_is_exception(self):
        """AuthenticationError is a subclass of Exception."""
        assert issubclass(AuthenticationError, Exception)
