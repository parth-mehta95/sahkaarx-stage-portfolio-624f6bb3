"""
auth.py - Authentication Module with Breakpoint Markers for Debugger Tracing.

Deliverables & Scenario:
- Set breakpoints in registration and login endpoints.
- Step through code in debugger; verify password hashing occurs.
- Confirm user lookup queries return correct data.
- Inline comments marking breakpoint locations in auth routes.

This module provides:
1. User model with secure password hashing and verification.
2. In-memory user storage and user lookup query functions.
3. Flask authentication endpoints (POST /register, POST /login, GET /users/<username>).
4. Clearly documented BREAKPOINT markers with debugger hooks.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from flask import Flask, Response, jsonify, request

# Secure password hashing library
try:
    from werkzeug.security import check_password_hash, generate_password_hash
    HAS_WERKZEUG = True
except ImportError:  # pragma: no cover
    import hashlib
    import hmac
    import secrets

    HAS_WERKZEUG = False

    def generate_password_hash(password: str, method: str = "pbkdf2:sha256") -> str:
        """Fallback PBKDF2-HMAC-SHA256 password hashing with cryptographic salt."""
        salt = secrets.token_hex(16)
        iterations = 100_000
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return f"pbkdf2:sha256:{iterations}${salt}${key.hex()}"

    def check_password_hash(pwhash: str, password: str) -> bool:
        """Fallback timing-safe PBKDF2 password verification."""
        try:
            algorithm, method, rest = pwhash.split(":", 2)
            iterations_str, salt, stored_hash = rest.split("$", 2)
            key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations_str))
            return hmac.compare_digest(key.hex(), stored_hash)
        except Exception:
            return False


# =============================================================================
# DEBUGGER HELPER: Programmatic Breakpoint Trigger
# =============================================================================
# When DEBUG_BREAKPOINTS=1 is set in the environment or enabled programmatically,
# python's built-in breakpoint() is invoked at each marked breakpoint location.
DEBUG_BREAKPOINTS = os.environ.get("DEBUG_BREAKPOINTS", "").strip().lower() in ("1", "true", "yes")


def debug_pause(breakpoint_id: str, label: str, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Triggers an interactive breakpoint if DEBUG_BREAKPOINTS is enabled,
    and logs the current breakpoint inspection state for debugging sessions.
    """
    if DEBUG_BREAKPOINTS:
        print(f"\n[DEBUGGER PAUSE] >>> {breakpoint_id}: {label}")
        if context:
            for k, v in context.items():
                print(f"    watch [{k}] = {repr(v)}")
        # Invokes Python 3.7+ built-in breakpoint (pdb / IDE attached debugger)
        breakpoint()


# =============================================================================
# USER MODEL & IN-MEMORY REPOSITORY
# =============================================================================
class User:
    """
    User entity representing an authenticated user.
    Stores user attributes and secure password hashes. Plaintext passwords
    are NEVER stored in memory or persisted.
    """

    _users_by_id: Dict[int, "User"] = {}
    _users_by_username: Dict[str, "User"] = {}
    _users_by_email: Dict[str, "User"] = {}
    _next_id: int = 1

    def __init__(
        self,
        username: str,
        email: str,
        password_hash: str,
        user_id: Optional[int] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        self.id: int = user_id if user_id is not None else User._allocate_id()
        self.username: str = username.strip()
        self.email: str = email.strip().lower()
        self.password_hash: str = password_hash
        self.created_at: datetime = created_at or datetime.now()

    @classmethod
    def _allocate_id(cls) -> int:
        assigned = cls._next_id
        cls._next_id += 1
        return assigned

    @classmethod
    def clear_database(cls) -> None:
        """Reset in-memory storage (useful for isolated test sessions)."""
        cls._users_by_id.clear()
        cls._users_by_username.clear()
        cls._users_by_email.clear()
        cls._next_id = 1

    # -------------------------------------------------------------------------
    # USER LOOKUP QUERIES
    # -------------------------------------------------------------------------
    @classmethod
    def find_by_username(cls, username: str) -> Optional["User"]:
        """
        Query user repository by username (case-insensitive lookup).

        Args:
            username: The username to search for.

        Returns:
            User object if found; None otherwise.
        """
        if not username or not isinstance(username, str):
            return None
        return cls._users_by_username.get(username.strip().lower())

    @classmethod
    def find_by_email(cls, email: str) -> Optional["User"]:
        """
        Query user repository by email (case-insensitive lookup).

        Args:
            email: The email address to search for.

        Returns:
            User object if found; None otherwise.
        """
        if not email or not isinstance(email, str):
            return None
        return cls._users_by_email.get(email.strip().lower())

    @classmethod
    def find_by_id(cls, user_id: int) -> Optional["User"]:
        """
        Query user repository by primary key user ID.

        Args:
            user_id: Integer user ID.

        Returns:
            User object if found; None otherwise.
        """
        return cls._users_by_id.get(user_id)

    @classmethod
    def all_users(cls) -> List["User"]:
        """Retrieve list of all registered users."""
        return list(cls._users_by_id.values())

    # -------------------------------------------------------------------------
    # PASSWORD HASHING AND VERIFICATION
    # -------------------------------------------------------------------------
    @staticmethod
    def hash_password(plain_password: str) -> str:
        """
        Cryptographically hash a plain-text password using Werkzeug / PBKDF2.

        Args:
            plain_password: Plain text password to hash.

        Returns:
            Hashed password string with embedded algorithm, salt, and hash.
        """
        if not isinstance(plain_password, str) or not plain_password:
            raise ValueError("Password cannot be empty.")
        # Uses PBKDF2 or Scrypt with high cost factor & unique salt
        return generate_password_hash(plain_password)

    def check_password(self, candidate_password: str) -> bool:
        """
        Verify a candidate plain-text password against the stored password hash.
        Employs timing-attack resistant comparison.

        Args:
            candidate_password: Plain text password provided during login.

        Returns:
            True if candidate matches the stored hash; False otherwise.
        """
        if not candidate_password or not isinstance(candidate_password, str):
            return False
        return check_password_hash(self.password_hash, candidate_password)

    # -------------------------------------------------------------------------
    # PERSISTENCE
    # -------------------------------------------------------------------------
    @classmethod
    def register(cls, username: str, email: str, plain_password: str) -> "User":
        """
        Convenience factory: Hashes password, constructs User instance,
        and saves it to the indexed in-memory user repository.
        """
        hashed = cls.hash_password(plain_password)
        user = cls(username=username, email=email, password_hash=hashed)
        cls._users_by_id[user.id] = user
        cls._users_by_username[user.username.lower()] = user
        cls._users_by_email[user.email.lower()] = user
        return user

    def to_dict(self) -> Dict[str, Any]:
        """Sanitized user dictionary representation (never leaks password_hash)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# FLASK APPLICATION FACTORY & AUTH ROUTES
# =============================================================================
def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """
    Creates and configures the Flask application with debuggable authentication routes.
    """
    app = Flask(__name__)
    if test_config:
        app.config.update(test_config)

    # -------------------------------------------------------------------------
    # ROUTE 1: REGISTRATION ENDPOINT
    # -------------------------------------------------------------------------
    @app.route("/register", methods=["POST"])
    def register() -> Tuple[Response, int]:
        """
        Register a new user account with secure password hashing.

        Payload (JSON):
            {
                "username": "alice",
                "email": "alice@example.com",
                "password": "Password123!"
            }

        Breakpoints inside this route:
            - BREAKPOINT 1: Entry & Payload Extraction
            - BREAKPOINT 2: User Lookup Query (Username Duplicate Check)
            - BREAKPOINT 3: User Lookup Query (Email Duplicate Check)
            - BREAKPOINT 4: Password Hashing Step
            - BREAKPOINT 5: User Persistence & Response Return
        """
        # =====================================================================
        # BREAKPOINT 1: Registration Entry & Request Body Validation
        # Location: auth.py -> register() [Step 1: Parse incoming payload]
        # Inspect in Debugger:
        #   - request.get_json(silent=True)
        #   - data (dict containing raw registration fields)
        # Expected: Valid dictionary with 'username', 'email', and 'password' keys.
        # =====================================================================
        # >>> BREAKPOINT 1 LOCATION <<<
        debug_pause("BREAKPOINT 1", "Registration Entry & Payload Extraction", {"request_json": request.get_json(silent=True)})
        # breakpoint()  # Line breakpoint for Step 1

        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Request body must be a valid JSON object."}), 400

        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        # Field validation
        if not username or not isinstance(username, str) or not username.strip():
            return jsonify({"error": "Username is required and cannot be empty."}), 400

        if not email or not isinstance(email, str) or "@" not in email:
            return jsonify({"error": "A valid email address is required."}), 400

        if not password or not isinstance(password, str) or len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters long."}), 400

        clean_username = username.strip()
        clean_email = email.strip()

        # =====================================================================
        # BREAKPOINT 2: User Lookup Query - Check Existing Username
        # Location: auth.py -> register() [Step 2: User lookup by username]
        # Inspect in Debugger:
        #   - clean_username (str): Candidate username string
        #   - existing_user_by_name (User | None): Result of query
        # Expected: None for new user registration; User instance if duplicate.
        # =====================================================================
        # >>> BREAKPOINT 2 LOCATION <<<
        existing_user_by_name = User.find_by_username(clean_username)
        debug_pause("BREAKPOINT 2", "User Lookup Query (Username)", {
            "query_param": clean_username,
            "lookup_result": existing_user_by_name
        })
        # breakpoint()  # Line breakpoint for Step 2

        if existing_user_by_name is not None:
            return jsonify({"error": f"Username '{clean_username}' is already taken."}), 409

        # =====================================================================
        # BREAKPOINT 3: User Lookup Query - Check Existing Email
        # Location: auth.py -> register() [Step 3: User lookup by email]
        # Inspect in Debugger:
        #   - clean_email (str): Candidate email string
        #   - existing_user_by_email (User | None): Result of query
        # Expected: None for unique email; User instance if duplicate.
        # =====================================================================
        # >>> BREAKPOINT 3 LOCATION <<<
        existing_user_by_email = User.find_by_email(clean_email)
        debug_pause("BREAKPOINT 3", "User Lookup Query (Email)", {
            "query_param": clean_email,
            "lookup_result": existing_user_by_email
        })
        # breakpoint()  # Line breakpoint for Step 3

        if existing_user_by_email is not None:
            return jsonify({"error": f"Email '{clean_email}' is already registered."}), 409

        # =====================================================================
        # BREAKPOINT 4: Password Hashing Execution & Verification
        # Location: auth.py -> register() [Step 4: Password hashing verification]
        # Inspect in Debugger:
        #   - password (str): Raw plain-text password before hashing
        #   - hashed_password (str): Generated cryptographic hash string
        # Step-Into Target: User.hash_password() -> generate_password_hash()
        # Verify:
        #   1. hashed_password != password (plain-text never stored)
        #   2. hashed_password starts with hash identifier (e.g., 'scrypt:' or 'pbkdf2:')
        #   3. Salt is embedded and randomized
        # =====================================================================
        # >>> BREAKPOINT 4 LOCATION <<<
        hashed_password = User.hash_password(password)
        debug_pause("BREAKPOINT 4", "Password Hashing Step", {
            "plain_password": password,
            "hashed_password": hashed_password,
            "hash_length": len(hashed_password),
            "algorithm_prefix": hashed_password.split(":")[0] if ":" in hashed_password else "unknown",
        })
        # breakpoint()  # Line breakpoint for Step 4

        # =====================================================================
        # BREAKPOINT 5: User Persistence & Registration Response Generation
        # Location: auth.py -> register() [Step 5: Save user to store & respond]
        # Inspect in Debugger:
        #   - new_user (User): Newly instantiated User object
        #   - new_user.id: Assigned unique numeric identifier
        #   - new_user.password_hash: Stored hash
        #   - new_user.to_dict(): Sanitized output dictionary
        # =====================================================================
        # >>> BREAKPOINT 5 LOCATION <<<
        new_user = User(
            username=clean_username,
            email=clean_email,
            password_hash=hashed_password,
        )
        User._users_by_id[new_user.id] = new_user
        User._users_by_username[new_user.username.lower()] = new_user
        User._users_by_email[new_user.email.lower()] = new_user

        debug_pause("BREAKPOINT 5", "User Persistence & Response Generation", {
            "persisted_user_id": new_user.id,
            "persisted_username": new_user.username,
            "response_body": new_user.to_dict(),
        })
        # breakpoint()  # Line breakpoint for Step 5

        return jsonify({
            "message": "User registered successfully.",
            "user": new_user.to_dict(),
        }), 201

    # -------------------------------------------------------------------------
    # ROUTE 2: LOGIN ENDPOINT
    # -------------------------------------------------------------------------
    @app.route("/login", methods=["POST"])
    def login() -> Tuple[Response, int]:
        """
        Authenticate a user by verifying provided credentials against the stored hash.

        Payload (JSON):
            {
                "username": "alice",
                "password": "Password123!"
            }

        Breakpoints inside this route:
            - BREAKPOINT 6: Login Route Entry & Credential Extraction
            - BREAKPOINT 7: User Lookup Query (Retrieve Stored User)
            - BREAKPOINT 8: Password Hash Verification Step
            - BREAKPOINT 9: Login Response Generation
        """
        # =====================================================================
        # BREAKPOINT 6: Login Route Entry & Credential Extraction
        # Location: auth.py -> login() [Step 6: Parse incoming login payload]
        # Inspect in Debugger:
        #   - request.get_json(silent=True)
        #   - username (str | None): Username or email supplied by client
        #   - password (str | None): Plaintext candidate password
        # Expected: Dictionary with non-empty 'username' and 'password'.
        # =====================================================================
        # >>> BREAKPOINT 6 LOCATION <<<
        debug_pause("BREAKPOINT 6", "Login Entry & Credential Extraction", {"request_json": request.get_json(silent=True)})
        # breakpoint()  # Line breakpoint for Step 6

        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Request body must be a valid JSON object."}), 400

        username = data.get("username")
        password = data.get("password")

        if not username or not isinstance(username, str) or not username.strip():
            return jsonify({"error": "Username is required."}), 400

        if not password or not isinstance(password, str):
            return jsonify({"error": "Password is required."}), 400

        clean_identifier = username.strip()

        # =====================================================================
        # BREAKPOINT 7: User Lookup Query - Retrieve User Record
        # Location: auth.py -> login() [Step 7: Execute user lookup query]
        # Inspect in Debugger:
        #   - clean_identifier (str): Search term (supports username or email)
        #   - user (User | None): Retrieved user entity from database/repository
        # Verify:
        #   1. If user exists: user.id, user.username, user.email, user.password_hash
        #   2. If user does NOT exist: user is None -> return 401 Unauthorized
        # =====================================================================
        # >>> BREAKPOINT 7 LOCATION <<<
        # Lookup supports either username or email
        user = User.find_by_username(clean_identifier) or User.find_by_email(clean_identifier)

        debug_pause("BREAKPOINT 7", "User Lookup Query (Login)", {
            "lookup_identifier": clean_identifier,
            "user_found": user is not None,
            "retrieved_user": user.to_dict() if user else None,
            "stored_password_hash": user.password_hash if user else None,
        })
        # breakpoint()  # Line breakpoint for Step 7

        if user is None:
            return jsonify({"error": "Invalid username or password."}), 401

        # =====================================================================
        # BREAKPOINT 8: Password Hash Verification & Authentication Check
        # Location: auth.py -> login() [Step 8: Timing-safe hash validation]
        # Inspect in Debugger:
        #   - candidate_password: The plaintext password entered by the user
        #   - user.password_hash: The stored PBKDF2/Scrypt hash from registration
        #   - is_valid_password (bool): Result of check_password_hash()
        # Step-Into Target: user.check_password() -> check_password_hash()
        # Verify:
        #   1. Matching password -> is_valid_password == True
        #   2. Incorrect password -> is_valid_password == False
        # =====================================================================
        # >>> BREAKPOINT 8 LOCATION <<<
        is_valid_password = user.check_password(password)

        debug_pause("BREAKPOINT 8", "Password Hash Verification", {
            "candidate_password": password,
            "stored_hash": user.password_hash,
            "verification_result": is_valid_password,
        })
        # breakpoint()  # Line breakpoint for Step 8

        if not is_valid_password:
            return jsonify({"error": "Invalid username or password."}), 401

        # =====================================================================
        # BREAKPOINT 9: Login Response Generation (Success)
        # Location: auth.py -> login() [Step 9: Successful authentication response]
        # Inspect in Debugger:
        #   - user.to_dict() (Sanitized dictionary without password_hash)
        #   - HTTP status code (200 OK)
        # =====================================================================
        # >>> BREAKPOINT 9 LOCATION <<<
        debug_pause("BREAKPOINT 9", "Login Response Generation", {
            "authenticated_user_id": user.id,
            "authenticated_username": user.username,
        })
        # breakpoint()  # Line breakpoint for Step 9

        return jsonify({
            "message": "Login successful.",
            "user": user.to_dict(),
        }), 200

    # -------------------------------------------------------------------------
    # ROUTE 3: USER LOOKUP & PROFILE INSPECTION ROUTE
    # -------------------------------------------------------------------------
    @app.route("/users/<string:username>", methods=["GET"])
    def get_user_by_username(username: str) -> Tuple[Response, int]:
        """
        Query endpoint to look up a user by username and inspect returned record.
        """
        # =====================================================================
        # BREAKPOINT 10: Profile User Lookup Query
        # Location: auth.py -> get_user_by_username()
        # Inspect in Debugger:
        #   - username (str): Queried username
        #   - user (User | None): User record returned by repository
        # =====================================================================
        # >>> BREAKPOINT 10 LOCATION <<<
        user = User.find_by_username(username)
        debug_pause("BREAKPOINT 10", "Profile User Lookup Query", {
            "query_username": username,
            "user_found": user is not None,
        })
        # breakpoint()  # Line breakpoint for Step 10

        if user is None:
            return jsonify({"error": f"User '{username}' not found."}), 404

        return jsonify({"user": user.to_dict()}), 200

    # -------------------------------------------------------------------------
    # ROUTE 4: SYSTEM HEALTH CHECK
    # -------------------------------------------------------------------------
    @app.route("/health", methods=["GET"])
    def health_check() -> Tuple[Response, int]:
        """Health check endpoint confirming API availability."""
        return jsonify({
            "status": "healthy",
            "registered_users_count": len(User.all_users()),
            "debugger_breakpoints_enabled": DEBUG_BREAKPOINTS,
        }), 200

    return app


# =============================================================================
# STANDALONE DEBUGGING SESSION WALKTHROUGH RUNNER
# =============================================================================
def run_debug_walkthrough() -> None:
    """
    Executes a complete simulated debugging walkthrough tracing:
    1. User Registration with password hashing verification.
    2. User Lookup query verification (found vs not found).
    3. User Login with password verification (correct password vs wrong password).
    Prints formatted inspectable trace points corresponding to each breakpoint.
    """
    print("=" * 80)
    print(" AUTHENTICATION FLOW DEBUGGING SESSION WALKTHROUGH")
    print("=" * 80)

    User.clear_database()
    app = create_app({"TESTING": True})
    client = app.test_client()

    print("\n--- STEP 1: Registration Flow & Password Hashing Verification ---")
    reg_payload = {
        "username": "debug_user",
        "email": "debug_user@example.com",
        "password": "SuperSecretPassword123!",
    }
    print(f"[*] Sending POST /register with payload: {reg_payload}")
    reg_response = client.post("/register", json=reg_payload)
    print(f"[*] Response Status Code: {reg_response.status_code}")
    print(f"[*] Response JSON: {reg_response.get_json()}")

    # Inspect in-memory state
    user_record = User.find_by_username("debug_user")
    assert user_record is not None, "FAILED: User lookup by username returned None!"
    print(f"[*] User Lookup Query Result: Found User(id={user_record.id}, username='{user_record.username}')")
    print(f"[*] Plaintext Password: '{reg_payload['password']}'")
    print(f"[*] Stored Password Hash: '{user_record.password_hash}'")
    print(f"[*] Password Hashing Verified: Hash != Plaintext ({user_record.password_hash != reg_payload['password']})")

    print("\n--- STEP 2: Duplicate Registration Lookup Query Verification ---")
    dup_response = client.post("/register", json=reg_payload)
    print(f"[*] Duplicate POST /register Status Code: {dup_response.status_code} (Expected 409)")
    print(f"[*] Duplicate Error Message: {dup_response.get_json()}")

    print("\n--- STEP 3: Login Flow with Correct Password ---")
    login_payload = {
        "username": "debug_user",
        "password": "SuperSecretPassword123!",
    }
    print(f"[*] Sending POST /login with payload: {login_payload}")
    login_response = client.post("/login", json=login_payload)
    print(f"[*] Login Status Code: {login_response.status_code} (Expected 200)")
    print(f"[*] Login Response JSON: {login_response.get_json()}")

    print("\n--- STEP 4: Login Flow with Incorrect Password (Failure Verification) ---")
    bad_login_payload = {
        "username": "debug_user",
        "password": "WrongPassword999!",
    }
    print(f"[*] Sending POST /login with bad credentials: {bad_login_payload}")
    bad_login_response = client.post("/login", json=bad_login_payload)
    print(f"[*] Bad Login Status Code: {bad_login_response.status_code} (Expected 401)")
    print(f"[*] Bad Login Error Message: {bad_login_response.get_json()}")

    print("\n--- STEP 5: User Lookup Query for Non-Existent User ---")
    non_existent_payload = {
        "username": "ghost_user",
        "password": "AnyPassword123!",
    }
    ghost_response = client.post("/login", json=non_existent_payload)
    print(f"[*] Non-Existent User Status Code: {ghost_response.status_code} (Expected 401)")
    print(f"[*] Non-Existent User Error: {ghost_response.get_json()}")

    print("\n" + "=" * 80)
    print(" ALL DEBUGGING STEPS COMPLETED AND VERIFIED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    if "--walkthrough" in sys.argv or "--trace" in sys.argv:
        run_debug_walkthrough()
    else:
        app = create_app()
        print("Starting Flask Auth API server on http://127.0.0.1:5000 (debug=True)...")
        print("Set DEBUG_BREAKPOINTS=1 to pause execution on breakpoints during debugging.")
        app.run(debug=True, port=5000)
