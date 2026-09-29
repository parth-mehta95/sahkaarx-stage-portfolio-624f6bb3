"""
test_auth.py - Comprehensive test cases for User Registration, Login, and Password Hashing.

Validates:
1. Passwords hashed before storage (Success criterion 1)
2. Login validates hashed password (Success criterion 2)
3. User.register() and User.login() methods / functions
4. Bcrypt and Hashlib password hashing mechanisms
5. Duplicate user prevention & input validation
6. Test registration and login with sample users (Submission guidance 3)
7. Flask registration endpoint (POST /register)
8. Flask login endpoint with hashing (POST /login)
9. Preservation of array-based task storage on User
"""
import pytest
from User import User, register, login
from Task import Task
from app import create_app


@pytest.fixture(autouse=True)
def reset_user_registry():
    """Ensure in-memory user registry is clean before and after every test."""
    User.clear_registry()
    yield
    User.clear_registry()


@pytest.fixture
def app():
    """Flask application fixture configured for testing."""
    test_app = create_app({"TESTING": True})
    return test_app


@pytest.fixture
def client(app):
    """Flask test client fixture."""
    return app.test_client()


# ======================================================================
# 1. Success Criterion 1: Passwords Hashed Before Storage
# ======================================================================


def test_password_hashed_before_storage_on_init():
    """Verify passwords passed at initialization are hashed, not stored plaintext."""
    raw_pass = "MySecretPass#2026"
    user = User(username="alice", email="alice@example.com", password=raw_pass)

    # Password is stored as hash, never plain text
    assert user.password_hash != raw_pass
    assert raw_pass not in user.password_hash
    assert len(user.password_hash) > 20
    assert user.password_hash.startswith(("sha256$", "pbkdf2:", "$2a$", "$2b$", "$2y$", "scrypt:"))


def test_password_hashed_before_storage_on_register():
    """Verify User.register() hashes passwords before storing them."""
    raw_pass = "RegistrationPass99!"
    user = User.register(username="bob", email="bob@example.com", password=raw_pass)

    assert user.password_hash != raw_pass
    assert raw_pass not in user.password_hash
    assert len(user.password_hash) > 20


def test_password_hash_salt_uniqueness():
    """Verify that hashing the same password twice produces distinct salt/hash outputs."""
    raw_pass = "IdenticalPassword123"
    hash1 = User.hash_password(raw_pass)
    hash2 = User.hash_password(raw_pass)

    assert hash1 != hash2  # Salt ensures hashes are unique even for same password


def test_hashlib_specific_hashing():
    """Verify hashlib SHA-256 implementation with cryptographic salt."""
    raw_pass = "HashlibPassword789"
    hash_str = User.hash_password(raw_pass, method="hashlib")

    assert hash_str.startswith("sha256$")
    parts = hash_str.split("$")
    assert len(parts) == 3
    salt_hex, digest = parts[1], parts[2]
    assert len(salt_hex) == 32  # 16 bytes = 32 hex chars
    assert len(digest) == 64    # SHA-256 = 64 hex chars


# ======================================================================
# 2. Success Criterion 2: Login Validates Hashed Password
# ======================================================================


def test_login_validates_hashed_password_success():
    """Verify that login succeeds when provided the correct plaintext password."""
    raw_pass = "CorrectHorseBatteryStaple"
    user = User.register(username="charlie", email="charlie@example.com", password=raw_pass)

    auth_user = User.login(username="charlie", password=raw_pass)
    assert auth_user is not None
    assert auth_user.id == user.id
    assert auth_user.username == "charlie"
    assert auth_user.email == "charlie@example.com"


def test_login_validates_hashed_password_wrong_password():
    """Verify that login fails and returns None when password does not match hash."""
    User.register(username="dana", email="dana@example.com", password="CorrectPassword123")

    # Invalid password attempts
    assert User.login(username="dana", password="WrongPassword123") is None
    assert User.login(username="dana", password="correctpassword123") is None  # Case sensitive
    assert User.login(username="dana", password="") is None


def test_login_with_nonexistent_user():
    """Verify that login returns None for an unregistered user."""
    assert User.login(username="ghost_user", password="AnyPassword") is None


def test_login_using_email():
    """Verify that login also allows authentication using the registered email."""
    raw_pass = "EmailAuthPass123!"
    user = User.register(username="elena", email="elena@example.com", password=raw_pass)

    auth_user = User.login(username="elena@example.com", password=raw_pass)
    assert auth_user is not None
    assert auth_user.id == user.id


def test_instance_login_method():
    """Verify that calling user.login(password) on an instance works as expected."""
    user = User.register(username="felix", email="felix@example.com", password="FelixSecretPassword")

    # Instance-level login check
    assert user.login("FelixSecretPassword") is True
    assert user.login("WrongSecret") is False


# ======================================================================
# 3. Submission Guidance 3: Test Registration and Login with Sample Users
# ======================================================================


def test_registration_and_login_with_sample_users():
    """
    Guidance step 3: Test registration and login with sample users.
    Simulates a realistic multi-user environment.
    """
    sample_users = [
        {"username": "john_doe", "email": "john@example.com", "password": "JohnStrongPassword#1"},
        {"username": "jane_smith", "email": "jane@example.com", "password": "JaneSecurePassword#2"},
        {"username": "alex_tech", "email": "alex@example.com", "password": "AlexDevPassword#3"},
    ]

    # 1. Register all sample users
    created_users = []
    for data in sample_users:
        u = User.register(username=data["username"], email=data["email"], password=data["password"])
        created_users.append(u)
        # Verify passwords hashed
        assert u.password_hash != data["password"]
        assert data["password"] not in u.password_hash

    assert len(User.get_all_users()) == 3

    # 2. Login each sample user with correct credentials
    for data in sample_users:
        authenticated = User.login(username=data["username"], password=data["password"])
        assert authenticated is not None
        assert authenticated.username == data["username"]
        assert authenticated.email == data["email"]

    # 3. Cross-credential attacks (trying Jane's password on John's account)
    assert User.login(username="john_doe", password=sample_users[1]["password"]) is None
    assert User.login(username="jane_smith", password=sample_users[0]["password"]) is None
    assert User.login(username="alex_tech", password="random_guess_password") is None


# ======================================================================
# 4. User Model Validations & Duplicate Prevention
# ======================================================================


def test_register_duplicate_username_rejected():
    """Verify that registering a duplicate username raises ValueError."""
    User.register(username="george", email="george1@example.com", password="pass")
    with pytest.raises(ValueError, match="already taken"):
        User.register(username="george", email="george2@example.com", password="pass")

    # Case insensitive duplicate check
    with pytest.raises(ValueError, match="already taken"):
        User.register(username="GEORGE", email="george3@example.com", password="pass")


def test_register_duplicate_email_rejected():
    """Verify that registering a duplicate email raises ValueError."""
    User.register(username="hannah", email="hannah@example.com", password="pass")
    with pytest.raises(ValueError, match="already registered"):
        User.register(username="hannah2", email="hannah@example.com", password="pass")

    # Case insensitive duplicate check
    with pytest.raises(ValueError, match="already registered"):
        User.register(username="hannah3", email="HANNAH@EXAMPLE.COM", password="pass")


def test_register_input_validations():
    """Verify type checking and value checks on registration."""
    with pytest.raises(ValueError):
        User.register(username="", email="valid@example.com", password="pwd")

    with pytest.raises(TypeError):
        User.register(username=123, email="valid@example.com", password="pwd")  # type: ignore

    with pytest.raises(ValueError):
        User.register(username="ian", email="invalid_email", password="pwd")

    with pytest.raises(ValueError):
        User.register(username="ian", email="ian@example.com", password="")


def test_module_level_register_and_login_aliases():
    """Verify module-level register and login functions work identically."""
    user = register(username="juliet", email="juliet@example.com", password="JulietPassword!")
    assert user.username == "juliet"

    auth = login(username="juliet", password="JulietPassword!")
    assert auth is not None
    assert auth.id == user.id


def test_user_truthiness_with_empty_tasks():
    """Verify user evaluates to True in boolean contexts even when task array is empty."""
    user = User.register(username="kevin", email="kevin@example.com", password="pwd")
    assert len(user.tasks) == 0
    # Must evaluate to True so `if user:` or `if User.login(...):` works
    assert bool(user) is True


# ======================================================================
# 5. Deliverable 1: Registration Endpoint (POST /register)
# ======================================================================


def test_api_register_endpoint_success(client):
    """Verify POST /register successfully registers user and returns 201 Created."""
    payload = {
        "username": "api_user",
        "email": "api_user@example.com",
        "password": "ApiPassword123!",
    }
    response = client.post("/register", json=payload)
    assert response.status_code == 201

    data = response.get_json()
    assert data["message"] == "User registered successfully."
    assert "user" in data
    assert data["user"]["username"] == "api_user"
    assert data["user"]["email"] == "api_user@example.com"
    # Raw password or password_hash should never be returned
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]

    # Verify user exists in backend with hashed password
    registered = User.get_by_username("api_user")
    assert registered is not None
    assert registered.password_hash != "ApiPassword123!"
    assert registered.check_password("ApiPassword123!") is True


def test_api_register_endpoint_missing_fields(client):
    """Verify POST /register returns 400 Bad Request when required fields are missing."""
    # Missing password
    resp = client.post("/register", json={"username": "test1", "email": "test1@example.com"})
    assert resp.status_code == 400
    assert "error" in resp.get_json()

    # Missing username
    resp = client.post("/register", json={"email": "test2@example.com", "password": "pass"})
    assert resp.status_code == 400

    # Missing email
    resp = client.post("/register", json={"username": "test3", "password": "pass"})
    assert resp.status_code == 400

    # Non-json payload
    resp = client.post("/register", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_api_register_endpoint_duplicate_rejection(client):
    """Verify POST /register returns 400 when attempting to register existing username/email."""
    payload = {
        "username": "existing_user",
        "email": "existing@example.com",
        "password": "Password123",
    }
    resp1 = client.post("/register", json=payload)
    assert resp1.status_code == 201

    # Attempt same username
    resp2 = client.post("/register", json={
        "username": "existing_user",
        "email": "other@example.com",
        "password": "Password123",
    })
    assert resp2.status_code == 400
    assert "already taken" in resp2.get_json()["error"]

    # Attempt same email
    resp3 = client.post("/register", json={
        "username": "another_user",
        "email": "existing@example.com",
        "password": "Password123",
    })
    assert resp3.status_code == 400
    assert "already registered" in resp3.get_json()["error"]


# ======================================================================
# 6. Deliverable 2: Login Endpoint with Hashing (POST /login)
# ======================================================================


def test_api_login_endpoint_success(client):
    """Verify POST /login validates hashed password and returns 200 OK."""
    User.register(username="logintest", email="logintest@example.com", password="LoginPass2026")

    response = client.post("/login", json={
        "username": "logintest",
        "password": "LoginPass2026",
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Login successful."
    assert data["user"]["username"] == "logintest"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


def test_api_login_endpoint_invalid_password(client):
    """Verify POST /login returns 401 Unauthorized when password does not match hash."""
    User.register(username="logintest2", email="logintest2@example.com", password="CorrectPass")

    response = client.post("/login", json={
        "username": "logintest2",
        "password": "WrongPassword",
    })
    assert response.status_code == 401
    assert "Invalid username or password" in response.get_json()["error"]


def test_api_login_endpoint_unknown_user(client):
    """Verify POST /login returns 401 Unauthorized for unknown user."""
    response = client.post("/login", json={
        "username": "unknown_user",
        "password": "AnyPassword",
    })
    assert response.status_code == 401
    assert "Invalid username or password" in response.get_json()["error"]


def test_api_login_endpoint_missing_parameters(client):
    """Verify POST /login returns 400 Bad Request on missing parameters."""
    resp = client.post("/login", json={"username": "user"})
    assert resp.status_code == 400

    resp = client.post("/login", json={"password": "pass"})
    assert resp.status_code == 400


# ======================================================================
# 7. Array-based Task Storage Integration
# ======================================================================


def test_registered_user_task_array_storage():
    """Verify that registered users store tasks in array as expected by Task Manager."""
    user = User.register(username="task_owner", email="owner@example.com", password="TaskOwnerPass1")
    assert isinstance(user.tasks, list)
    assert len(user.tasks) == 0

    t1 = Task(title="Complete Week 01 Deliverables", description="Registration & Login")
    t2 = Task(title="Run Test Suite", description="Verify all auth cases")

    user.add_task(t1)
    user.add_task(t2)

    assert len(user.tasks) == 2
    assert user.get_tasks() == [t1, t2]
    assert user.tasks[0] == t1
    assert user.tasks[1] == t2

    dict_repr = user.to_dict()
    assert dict_repr["task_count"] == 2
    assert len(dict_repr["tasks"]) == 2
