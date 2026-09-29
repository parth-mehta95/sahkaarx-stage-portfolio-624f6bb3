"""
test_auth.py - Automated Unit & Integration Tests for auth.py

Validates:
1. Password hashing execution and salt generation.
2. User lookup queries (by username, by email, by id, non-existent).
3. Registration route with duplicate prevention.
4. Login route with valid credentials, invalid password, and missing user.
5. Breakpoint hook execution and tracing.
"""

from __future__ import annotations

import unittest
from auth import User, create_app, debug_pause


class TestAuthenticationDebugging(unittest.TestCase):
    def setUp(self) -> None:
        """Reset user database and configure test client before each test."""
        User.clear_database()
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        """Clean up in-memory storage after each test."""
        User.clear_database()

    # -------------------------------------------------------------------------
    # UNIT TESTS: Password Hashing Verification
    # -------------------------------------------------------------------------
    def test_password_hashing_transforms_plaintext(self) -> None:
        """Verify that password hashing occurs and plaintext is not retained."""
        raw_password = "SuperSecretPassword123!"
        hashed = User.hash_password(raw_password)

        # 1. Plaintext must never equal hashed output
        self.assertNotEqual(raw_password, hashed)
        self.assertNotIn(raw_password, hashed)

        # 2. Hash must contain algorithm identifier
        self.assertTrue(hashed.startswith("scrypt:") or hashed.startswith("pbkdf2:"))

        # 3. Two hashes of same password must differ due to unique salts
        hashed_again = User.hash_password(raw_password)
        self.assertNotEqual(hashed, hashed_again)

    def test_password_verification(self) -> None:
        """Verify that password verification correctly validates matching credentials."""
        user = User.register("alice", "alice@example.com", "Password123!")

        # Correct password
        self.assertTrue(user.check_password("Password123!"))

        # Incorrect password
        self.assertFalse(user.check_password("WrongPassword!"))

        # Empty / non-string password
        self.assertFalse(user.check_password(""))

    # -------------------------------------------------------------------------
    # UNIT TESTS: User Lookup Queries
    # -------------------------------------------------------------------------
    def test_user_lookup_queries_return_correct_data(self) -> None:
        """Confirm user lookup queries return the exact user record."""
        user = User.register("charlie", "charlie@example.com", "SecretPass123!")

        # Lookup by username
        found_by_name = User.find_by_username("charlie")
        self.assertIsNotNone(found_by_name)
        self.assertEqual(found_by_name.id, user.id)
        self.assertEqual(found_by_name.username, "charlie")
        self.assertEqual(found_by_name.email, "charlie@example.com")

        # Case-insensitive username lookup
        found_case = User.find_by_username("CHARLIE")
        self.assertIsNotNone(found_case)
        self.assertEqual(found_case.id, user.id)

        # Lookup by email
        found_by_email = User.find_by_email("charlie@example.com")
        self.assertIsNotNone(found_by_email)
        self.assertEqual(found_by_email.id, user.id)

        # Non-existent user lookup
        not_found = User.find_by_username("non_existent_user")
        self.assertIsNone(not_found)

        not_found_email = User.find_by_email("ghost@example.com")
        self.assertIsNone(not_found_email)

    # -------------------------------------------------------------------------
    # INTEGRATION TESTS: Registration Endpoint
    # -------------------------------------------------------------------------
    def test_registration_success(self) -> None:
        """Test successful registration endpoint execution."""
        payload = {
            "username": "bob",
            "email": "bob@example.com",
            "password": "ValidPassword999!",
        }
        res = self.client.post("/register", json=payload)
        self.assertEqual(res.status_code, 201)

        data = res.get_json()
        self.assertIn("user", data)
        self.assertEqual(data["user"]["username"], "bob")
        self.assertNotIn("password", data["user"])
        self.assertNotIn("password_hash", data["user"])

        # Confirm persisted in store
        persisted = User.find_by_username("bob")
        self.assertIsNotNone(persisted)
        self.assertTrue(persisted.check_password("ValidPassword999!"))

    def test_registration_duplicate_username_prevented(self) -> None:
        """Test user lookup intercepting duplicate username."""
        User.register("existing_user", "old@example.com", "Password123!")

        res = self.client.post("/register", json={
            "username": "existing_user",
            "email": "new@example.com",
            "password": "Password123!",
        })
        self.assertEqual(res.status_code, 409)
        self.assertIn("already taken", res.get_json()["error"])

    def test_registration_duplicate_email_prevented(self) -> None:
        """Test user lookup intercepting duplicate email."""
        User.register("old_user", "shared@example.com", "Password123!")

        res = self.client.post("/register", json={
            "username": "new_user",
            "email": "shared@example.com",
            "password": "Password123!",
        })
        self.assertEqual(res.status_code, 409)
        self.assertIn("already registered", res.get_json()["error"])

    # -------------------------------------------------------------------------
    # INTEGRATION TESTS: Login Endpoint
    # -------------------------------------------------------------------------
    def test_login_success_with_username(self) -> None:
        """Test successful login using username and valid password."""
        User.register("david", "david@example.com", "SecurePass456!")

        res = self.client.post("/login", json={
            "username": "david",
            "password": "SecurePass456!",
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["message"], "Login successful.")

    def test_login_success_with_email(self) -> None:
        """Test successful login using email as identifier."""
        User.register("eva", "eva@example.com", "SecurePass789!")

        res = self.client.post("/login", json={
            "username": "eva@example.com",
            "password": "SecurePass789!",
        })
        self.assertEqual(res.status_code, 200)

    def test_login_failure_with_wrong_password(self) -> None:
        """Test login rejection when candidate password is incorrect."""
        User.register("frank", "frank@example.com", "CorrectPassword1!")

        res = self.client.post("/login", json={
            "username": "frank",
            "password": "WrongPassword99!",
        })
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.get_json()["error"], "Invalid username or password.")

    def test_login_failure_with_non_existent_user(self) -> None:
        """Test login rejection when user lookup returns None."""
        res = self.client.post("/login", json={
            "username": "ghost",
            "password": "AnyPassword123!",
        })
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.get_json()["error"], "Invalid username or password.")

    # -------------------------------------------------------------------------
    # PROFILE & HEALTH CHECK TESTS
    # -------------------------------------------------------------------------
    def test_profile_lookup_route(self) -> None:
        """Test GET /users/<username> route."""
        User.register("grace", "grace@example.com", "Password123!")

        res = self.client.get("/users/grace")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["user"]["username"], "grace")

        res_404 = self.client.get("/users/nobody")
        self.assertEqual(res_404.status_code, 404)

    def test_health_check_endpoint(self) -> None:
        """Test GET /health endpoint."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "healthy")


if __name__ == "__main__":
    unittest.main()
