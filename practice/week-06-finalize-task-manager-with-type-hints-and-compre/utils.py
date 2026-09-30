"""
utils.py - Utility Functions and Type-Hinted Helpers for Task Manager.

Separation of Concerns:
This module encapsulates cross-cutting helper functions:
1. Cryptographic password hashing and verification.
2. Input validation for users, passwords, and task payloads.
3. HTTP request parsing and structured JSON response formatting.
4. Custom domain exception hierarchy.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Any, Dict, Optional, Tuple, Union
from flask import Response, jsonify, request

try:
    from werkzeug.security import check_password_hash, generate_password_hash
    HAS_WERKZEUG: bool = True
except ImportError:  # pragma: no cover
    HAS_WERKZEUG = False


# =============================================================================
# Custom Exception Hierarchy
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

    salt: str = secrets.token_hex(16)
    digest: str = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
    return f"sha256${salt}${digest}"


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a stored cryptographic hash.

    Args:
        password: The plaintext candidate password.
        hashed: The stored password hash.

    Returns:
        True if the candidate password matches the hash, False otherwise.
    """
    if not password or not hashed or not isinstance(password, str) or not isinstance(hashed, str):
        return False

    if HAS_WERKZEUG and not hashed.startswith("sha256$"):
        try:
            return bool(check_password_hash(hashed, password))
        except ValueError:
            pass

    if hashed.startswith("sha256$"):
        parts = hashed.split("$")
        if len(parts) == 3:
            _, salt, expected_digest = parts
            actual_digest: str = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
            return hmac.compare_digest(actual_digest, expected_digest)

    if HAS_WERKZEUG:
        try:
            return bool(check_password_hash(hashed, password))
        except Exception:
            return False

    return False


# =============================================================================
# 2. Input Validation Helpers
# =============================================================================

_USERNAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_-]{3,30}$")
_EMAIL_PATTERN: re.Pattern[str] = re.compile(r"^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$")
_VALID_STATUSES: set[str] = {"pending", "in_progress", "completed", "archived"}


def validate_username(username: Any) -> str:
    """
    Validate username format and length constraints.

    Args:
        username: The candidate username string.

    Returns:
        Cleaned, stripped username string.

    Raises:
        ValidationError: If username is empty, wrong type, or invalid format.
    """
    if username is None or not isinstance(username, str):
        raise ValidationError("Username must be a valid string.")

    cleaned: str = username.strip()
    if len(cleaned) < 3:
        raise ValidationError("Username must be at least 3 characters long.")
    if len(cleaned) > 30:
        raise ValidationError("Username cannot exceed 30 characters.")
    if not _USERNAME_PATTERN.match(cleaned):
        raise ValidationError("Username must contain only alphanumeric characters, underscores, or hyphens.")

    return cleaned


def validate_password_strength(password: Any, min_length: int = 6) -> str:
    """
    Validate that password meets minimal length and complexity requirements.

    Args:
        password: Candidate password string.
        min_length: Minimum character length required (default 6).

    Returns:
        Validated password string.

    Raises:
        ValidationError: If password fails length or type requirements.
    """
    if password is None or not isinstance(password, str):
        raise ValidationError("Password must be a valid string.")

    if len(password) < min_length:
        raise ValidationError(f"Password must be at least {min_length} characters long.")

    return password


def validate_email_format(email: Any) -> str:
    """
    Validate email string format.

    Args:
        email: Candidate email string.

    Returns:
        Cleaned, lowercased email string.

    Raises:
        ValidationError: If email is empty, wrong type, or improperly formatted.
    """
    if email is None or not isinstance(email, str):
        raise ValidationError("Email must be a valid string.")

    cleaned: str = email.strip().lower()
    if not cleaned or not _EMAIL_PATTERN.match(cleaned):
        raise ValidationError(f"Invalid email address format: '{email}'.")

    return cleaned


def validate_task_status(status: Any) -> str:
    """
    Validate task status string and normalize to allowed vocabulary.

    Args:
        status: Candidate status string (e.g., 'pending', 'in_progress', 'completed').

    Returns:
        Normalized status string.

    Raises:
        ValidationError: If status is not in allowed status values.
    """
    if status is None or not isinstance(status, str):
        raise ValidationError("Task status must be a string.")

    normalized: str = status.strip().lower().replace(" ", "_")

    alias_map: Dict[str, str] = {
        "todo": "pending",
        "in-progress": "in_progress",
        "doing": "in_progress",
        "done": "completed",
        "complete": "completed",
    }
    normalized = alias_map.get(normalized, normalized)

    if normalized not in _VALID_STATUSES:
        raise ValidationError(
            f"Invalid task status '{status}'. Allowed statuses: {sorted(_VALID_STATUSES)}."
        )

    return normalized


def validate_task_payload(data: Any, require_title: bool = True) -> Dict[str, Any]:
    """
    Validate task payload dictionary before creation or update.

    Args:
        data: Input payload dictionary.
        require_title: Whether title is strictly required (True for creation).

    Returns:
        Sanitized and validated task payload dictionary.

    Raises:
        ValidationError: If any field fails validation constraints.
    """
    if not isinstance(data, dict):
        raise ValidationError("Payload must be a JSON object dictionary.")

    sanitized: Dict[str, Any] = {}

    # Title validation
    if "title" in data:
        raw_title = data.get("title")
        if raw_title is None or not str(raw_title).strip():
            raise ValidationError("Task title cannot be empty.")
        sanitized["title"] = str(raw_title).strip()
    elif "name" in data:
        raw_name = data.get("name")
        if raw_name is None or not str(raw_name).strip():
            raise ValidationError("Task title cannot be empty.")
        sanitized["title"] = str(raw_name).strip()
    elif require_title:
        raise ValidationError("Task title is required.")

    # Description validation
    if "description" in data:
        raw_desc = data.get("description")
        sanitized["description"] = str(raw_desc).strip() if raw_desc is not None else ""

    # Status validation
    if "status" in data and data["status"] is not None:
        sanitized["status"] = validate_task_status(data["status"])

    # User ID association
    if "user_id" in data:
        sanitized["user_id"] = str(data["user_id"]) if data["user_id"] is not None else None

    # Completed boolean flag
    if "completed" in data and data["completed"] is not None:
        val = data["completed"]
        if isinstance(val, bool):
            sanitized["completed"] = val
        elif isinstance(val, str):
            sanitized["completed"] = val.strip().lower() in ("true", "1", "yes")
        else:
            sanitized["completed"] = bool(val)
        if sanitized["completed"]:
            sanitized["status"] = "completed"

    return sanitized


# =============================================================================
# 3. HTTP Request & Response Helpers
# =============================================================================

def get_request_data() -> Dict[str, Any]:
    """
    Safely extract JSON body or form data from the current Flask request.

    Returns:
        Dictionary containing parsed request parameters, or empty dict.
    """
    if request.is_json:
        data = request.get_json(silent=True)
        if isinstance(data, dict):
            return data
        return {}

    if request.form:
        return dict(request.form)

    return {}


def json_response(
    data: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
    message: Optional[str] = None,
) -> Tuple[Response, int]:
    """
    Build a standard structured JSON HTTP response.

    Args:
        data: Optional dictionary payload to embed.
        status_code: HTTP response status code (default 200).
        message: Optional human-readable message string.

    Returns:
        Tuple of (Flask Response, HTTP status code).
    """
    body: Dict[str, Any] = {"success": 200 <= status_code < 300}

    if message is not None:
        body["message"] = message

    if data:
        body.update(data)

    resp: Response = jsonify(body)
    return resp, status_code


def error_response(
    message: str,
    status_code: int = 400,
    details: Optional[Any] = None,
) -> Tuple[Response, int]:
    """
    Build a standard error JSON HTTP response.

    Args:
        message: Human-readable error description.
        status_code: HTTP error status code (default 400).
        details: Optional supplementary diagnostics.

    Returns:
        Tuple of (Flask Response, HTTP status code).
    """
    body: Dict[str, Any] = {
        "success": False,
        "error": message,
    }
    if details is not None:
        body["details"] = details

    resp: Response = jsonify(body)
    return resp, status_code
