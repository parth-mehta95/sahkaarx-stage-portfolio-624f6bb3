"""
utils.py - Utility Functions for Task Manager Application.

Separation of Concerns:
This module encapsulates all reusable cross-cutting helper functions:
1. Cryptographic password hashing and verification.
2. Input validation for users, passwords, and task data.
3. HTTP request payload parsing and response formatting.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import re
import secrets
from typing import Any, Dict, Optional, Tuple, Union
from flask import Response, jsonify, request

try:
    from werkzeug.security import check_password_hash, generate_password_hash
    HAS_WERKZEUG = True
except ImportError:  # pragma: no cover
    HAS_WERKZEUG = False


# =============================================================================
# Custom Exceptions
# =============================================================================

class ValidationError(ValueError):
    """Raised when user or task input validation fails."""
    pass


class AuthenticationError(Exception):
    """Raised when authentication credentials fail validation."""
    pass


class UserAlreadyExistsError(ValueError):
    """Raised when attempting to register a username or email that already exists."""
    pass


class NotFoundError(KeyError):
    """Raised when a requested resource is not found."""
    pass


# =============================================================================
# 1. Cryptographic Password Hashing & Verification
# =============================================================================

def hash_password(password: str, method: str = "pbkdf2:sha256") -> str:
    """
    Generate a secure cryptographic hash for the given plaintext password.

    Args:
        password: Plaintext password string.
        method: Hashing method specification.

    Returns:
        Salted cryptographic hash string.
    """
    if not password or not isinstance(password, str):
        raise ValidationError("Password must be a non-empty string.")

    if HAS_WERKZEUG:
        return generate_password_hash(password, method=method)

    # Secure fallback using PBKDF2-HMAC-SHA256 with 100,000 iterations & 16-byte random salt
    salt = secrets.token_hex(16)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2:sha256:{iterations}${salt}${derived.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a plaintext password against a stored cryptographic hash in constant time.

    Args:
        password: Plaintext password to verify.
        password_hash: Stored hash string.

    Returns:
        True if password matches hash, False otherwise.
    """
    if not password or not password_hash or not isinstance(password, str) or not isinstance(password_hash, str):
        return False

    if HAS_WERKZEUG:
        try:
            return check_password_hash(password_hash, password)
        except Exception:
            pass

    # Timing-safe verification for fallback format
    try:
        if password_hash.startswith("pbkdf2:sha256:"):
            prefix, rest = password_hash.split("pbkdf2:sha256:", 1)
            parts = rest.split("$")
            if len(parts) == 3:
                iterations = int(parts[0])
                salt = parts[1]
                stored_hash = parts[2]
                derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
                return hmac.compare_digest(derived.hex(), stored_hash)
        # Fallback comparison if plain string or unknown format
        return hmac.compare_digest(password_hash, password)
    except Exception:
        return False


# =============================================================================
# 2. Input Validation Helpers
# =============================================================================

def validate_username(username: Any) -> str:
    """
    Validate username requirements: non-empty, string, 3-30 characters, alphanumeric/underscores/hyphens.

    Args:
        username: Provided username candidate.

    Returns:
        Cleaned, stripped username string.

    Raises:
        ValidationError: If validation fails.
    """
    if username is None or not isinstance(username, str):
        raise ValidationError("Username must be a valid non-empty string.")

    cleaned = username.strip()
    if not cleaned:
        raise ValidationError("Username cannot be empty or whitespace.")

    if len(cleaned) < 3:
        raise ValidationError("Username must be at least 3 characters long.")

    if len(cleaned) > 50:
        raise ValidationError("Username must not exceed 50 characters.")

    if not re.match(r"^[A-Za-z0-9_\-\.]+$", cleaned):
        raise ValidationError("Username can only contain alphanumeric characters, underscores, hyphens, and periods.")

    return cleaned


def validate_password_strength(password: Any, min_length: int = 6) -> str:
    """
    Validate password requirements: non-empty, string, minimum length.

    Args:
        password: Provided plaintext password candidate.
        min_length: Minimum character length required (default 6).

    Returns:
        Unmodified password string if valid.

    Raises:
        ValidationError: If validation fails.
    """
    if password is None or not isinstance(password, str):
        raise ValidationError("Password must be a string.")

    if len(password) < min_length:
        raise ValidationError(f"Password must be at least {min_length} characters long.")

    return password


def validate_email_format(email: Any) -> str:
    """
    Validate optional email address format.

    Args:
        email: Provided email candidate.

    Returns:
        Cleaned, lowercased email string (or empty string if not provided).

    Raises:
        ValidationError: If non-empty but invalid format.
    """
    if email is None or email == "":
        return ""

    if not isinstance(email, str):
        raise ValidationError("Email must be a string.")

    cleaned = email.strip().lower()
    if not cleaned:
        return ""

    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(email_regex, cleaned):
        raise ValidationError(f"Invalid email address format: '{email}'.")

    return cleaned


def validate_task_status(status: Any) -> str:
    """
    Validate and normalize task status ('pending', 'in_progress', 'completed').

    Args:
        status: Provided status string.

    Returns:
        Normalized status string.

    Raises:
        ValidationError: If status is invalid.
    """
    valid_statuses = {"pending", "in_progress", "completed"}
    if not status:
        return "pending"

    status_str = str(status).strip().lower()
    # Normalize aliases
    if status_str in {"done", "finished"}:
        status_str = "completed"
    elif status_str in {"active", "doing", "progress"}:
        status_str = "in_progress"
    elif status_str in {"todo", "open"}:
        status_str = "pending"

    if status_str not in valid_statuses:
        raise ValidationError(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}.")

    return status_str


def validate_task_payload(data: Dict[str, Any], require_title: bool = True) -> Dict[str, Any]:
    """
    Validate and sanitize task creation/update payload.

    Args:
        data: Raw dictionary payload.
        require_title: Whether the 'title' field is strictly required.

    Returns:
        Cleaned task payload dictionary.

    Raises:
        ValidationError: If required fields are missing or invalid.
    """
    if not isinstance(data, dict):
        raise ValidationError("Payload must be a JSON object.")

    validated: Dict[str, Any] = {}

    # Title check
    if require_title or "title" in data or "name" in data:
        title = data.get("title") if "title" in data else data.get("name")
        if title is None or not str(title).strip():
            raise ValidationError("Task title is required and cannot be empty.")
        validated["title"] = str(title).strip()

    # Description
    if "description" in data:
        desc = data.get("description")
        validated["description"] = str(desc).strip() if desc is not None else ""

    # Status
    if "status" in data:
        validated["status"] = validate_task_status(data["status"])

    # User ID association
    if "user_id" in data:
        validated["user_id"] = str(data["user_id"]) if data["user_id"] is not None else None

    return validated


# =============================================================================
# 3. HTTP Request & Response Formatting Helpers
# =============================================================================

def get_request_data() -> Dict[str, Any]:
    """
    Extract request body payload cleanly from JSON, form-data, or raw data.

    Returns:
        Dict[str, Any]: Parsed request payload dictionary.
    """
    if request.is_json:
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            return payload
        return {}

    if request.form:
        return dict(request.form)

    try:
        data = request.get_json(force=True, silent=True)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return {}


def json_response(
    data: Any = None,
    status_code: int = 200,
    message: Optional[str] = None,
    **kwargs: Any,
) -> Tuple[Response, int]:
    """
    Standardized helper to generate JSON response tuples for Flask routes.

    Args:
        data: Primary response payload.
        status_code: HTTP response status code.
        message: Optional human-readable message.
        kwargs: Additional key-value pairs to include in the JSON response.

    Returns:
        Tuple[Response, int]: Flask response and status code.
    """
    body: Dict[str, Any] = {"status_code": status_code}

    if message is not None:
        body["message"] = message

    if isinstance(data, dict):
        body.update(data)
    elif data is not None:
        body["data"] = data

    body.update(kwargs)
    return jsonify(body), status_code


def error_response(message: str, status_code: int = 400, **kwargs: Any) -> Tuple[Response, int]:
    """
    Standardized helper to format JSON error responses.

    Args:
        message: Error description.
        status_code: HTTP error status code.
        kwargs: Additional error fields.

    Returns:
        Tuple[Response, int]: Flask error response and status code.
    """
    body = {
        "error": message,
        "status_code": status_code,
    }
    body.update(kwargs)
    return jsonify(body), status_code
