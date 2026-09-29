"""
test_auth.py - Automated Test Suite for OOP Authentication Refactoring.

Tests:
1. User.register() class method creates user, securely hashes password, and persists.
2. User.register() prevents duplicate usernames and validates inputs.
3. User.authenticate() authenticates valid credentials and rejects invalid passwords.
4. User class encapsulation: private attributes, property access, hidden password.
5. Flask routes delegate to User class methods with proper HTTP status codes.
6. Error handling for missing credentials (400), invalid credentials (401), and conflicts (409).
"""

from __future__ import annotations

import json
import unittest

from models import (
    AuthenticationError,
    Task,
    User,
    UserAlreadyExistsError,
    ValidationError,
)
from routes import app


class TestUserOOPAuthentication(unittest.TestCase):
    """Test suite validating OOP encapsulation and User class authentication methods."""

    def setUp(self) -> None:
        """Clear registry and setup test client before each test."""
        User.clear_all()
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        """Clean up registry after each test."""
        User.clear_all()

    # =========================================================================
    # 1. User.register() Class Method Tests
    # =========================================================================

    def test_user_register_success(self) -> None:
        """Verify User.register() class method creates and returns a valid User object."""
        user = User.register("john_doe", "SuperSecretPass123", email="john@example.com")

        self.assertIsNotNone(user)
        self.assertEqual(user.username, "john_doe")
        self.assertEqual(user.email, "john@example.com")
        self.assertIsNotNone(user.id)
        # Verify password is NOT stored as plaintext
        self.assertNotEqual(user.password_hash, "SuperSecretPass123")
        # Verify password can be verified
        self.assertTrue(user.verify_password("SuperSecretPass123"))

    def test_user_register_duplicate_username_raises_error(self) -> None:
        """Verify User.register() raises UserAlreadyExistsError on duplicate username."""
        User.register("alice", "Password123")
        with self.assertRaises(UserAlreadyExistsError):
            User.register("alice", "AnotherPassword456")

    def test_user_register_empty_username_raises_validation_error(self) -> None:
        """Verify User.register() rejects empty or whitespace username."""
        with self.assertRaises(ValidationError):
            User.register("", "ValidPassword123")
        with self.assertRaises(ValidationError):
            User.register("   ", "ValidPassword123")

    def test_user_register_empty_or_short_password_raises_validation_error(self) -> None:
        """Verify User.register() rejects empty or too short password."""
        with self.assertRaises(ValidationError):
            User.register("validuser", "")
        with self.assertRaises(ValidationError):
            User.register("validuser", "ab")

    # =========================================================================
    # 2. User.authenticate() Method Tests
    # =========================================================================

    def test_user_authenticate_valid_credentials(self) -> None:
        """Verify User.authenticate() returns User instance upon valid credentials."""
        User.register("bob", "Secret1234")
        auth_user = User.authenticate("bob", "Secret1234")

        self.assertIsNotNone(auth_user)
        self.assertIsInstance(auth_user, User)
        self.assertEqual(auth_user.username, "bob")

    def test_user_authenticate_invalid_password_returns_none(self) -> None:
        """Verify User.authenticate() returns None when password does not match."""
        User.register("bob", "CorrectPassword1")
        result = User.authenticate("bob", "WrongPassword99")

        self.assertIsNone(result)

    def test_user_authenticate_nonexistent_user_returns_none(self) -> None:
        """Verify User.authenticate() returns None when user does not exist."""
        result = User.authenticate("nonexistent_user", "AnyPassword123")
        self.assertIsNone(result)

    def test_user_authenticate_empty_inputs_returns_none(self) -> None:
        """Verify User.authenticate() returns None when username or password is empty."""
        self.assertIsNone(User.authenticate("", "pass"))
        self.assertIsNone(User.authenticate("user", ""))
        self.assertIsNone(User.authenticate("", ""))

    # =========================================================================
    # 3. Encapsulation & Security Tests
    # =========================================================================

    def test_user_password_property_encapsulation(self) -> None:
        """Verify user.password raises AttributeError when read (security encapsulation)."""
        user = User.register("carol", "SecretPass123")
        with self.assertRaises(AttributeError):
            _ = user.password

    def test_user_password_setter_encapsulation(self) -> None:
        """Verify setting user.password re-hashes and allows verification with new password."""
        user = User.register("dave", "InitialPass123")
        self.assertTrue(user.verify_password("InitialPass123"))

        # Update password via setter
        user.password = "NewUpdatedPass999"
        self.assertFalse(user.verify_password("InitialPass123"))
        self.assertTrue(user.verify_password("NewUpdatedPass999"))

    def test_user_to_dict_never_exposes_password_or_hash(self) -> None:
        """Verify serialized dictionary contains no sensitive password hash."""
        user = User.register("eve", "EveSecretPass")
        user_dict = user.to_dict()

        self.assertNotIn("password", user_dict)
        self.assertNotIn("password_hash", user_dict)
        self.assertNotIn("_password_hash", user_dict)
        self.assertEqual(user_dict["username"], "eve")

    # =========================================================================
    # 4. Flask Route Delegation Tests: POST /register
    # =========================================================================

    def test_route_register_success_status_201(self) -> None:
        """Verify POST /register delegates to User.register and returns HTTP 201 Created."""
        payload = {
            "username": "frank",
            "password": "FrankStrongPassword!",
            "email": "frank@example.com",
        }
        res = self.client.post(
            "/register",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["status_code"], 201)
        self.assertEqual(data["user"]["username"], "frank")
        self.assertEqual(data["user"]["email"], "frank@example.com")
        self.assertNotIn("password", data["user"])

        # Confirm user is persisted in User registry
        self.assertIsNotNone(User.get_by_username("frank"))

    def test_route_register_missing_username_returns_400(self) -> None:
        """Verify POST /register returns 400 Bad Request when username is missing."""
        payload = {"password": "Password123"}
        res = self.client.post(
            "/register",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)

    def test_route_register_missing_password_returns_400(self) -> None:
        """Verify POST /register returns 400 Bad Request when password is missing."""
        payload = {"username": "grace"}
        res = self.client.post(
            "/register",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)

    def test_route_register_duplicate_username_returns_409(self) -> None:
        """Verify POST /register returns 409 Conflict when username is already taken."""
        User.register("heidi", "Password123")
        payload = {"username": "heidi", "password": "NewPassword456"}
        res = self.client.post(
            "/register",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 409)
        data = res.get_json()
        self.assertIn("error", data)

    # =========================================================================
    # 5. Flask Route Delegation Tests: POST /login
    # =========================================================================

    def test_route_login_success_status_200(self) -> None:
        """Verify POST /login delegates to User.authenticate and returns HTTP 200 OK."""
        User.register("ivan", "IvanPass1234")
        payload = {"username": "ivan", "password": "IvanPass1234"}
        res = self.client.post(
            "/login",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status_code"], 200)
        self.assertEqual(data["user"]["username"], "ivan")

    def test_route_login_invalid_password_returns_401(self) -> None:
        """Verify POST /login returns 401 Unauthorized for incorrect password."""
        User.register("judy", "JudySecretPass")
        payload = {"username": "judy", "password": "WrongPassword"}
        res = self.client.post(
            "/login",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertIn("error", data)

    def test_route_login_nonexistent_user_returns_401(self) -> None:
        """Verify POST /login returns 401 Unauthorized for unknown username."""
        payload = {"username": "unknown_user", "password": "AnyPassword"}
        res = self.client.post(
            "/login",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertIn("error", data)

    def test_route_login_missing_fields_returns_400(self) -> None:
        """Verify POST /login returns 400 Bad Request when credentials are missing."""
        res = self.client.post("/login", data=json.dumps({}), content_type="application/json")
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
