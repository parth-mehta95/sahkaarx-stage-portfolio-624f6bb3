# Implement User Registration and Login with Password Hashing

## Task Brief
Add registration and login endpoints with password hashing; verify authentication flow works correctly.

## Scenario
Extend the Task Manager with secure user registration and login. Users must be able to create accounts and authenticate safely.

## Deliverables
- **Registration endpoint**: `POST /register` accepting user credentials and returning sanitized user profile.
- **Login endpoint with hashing**: `POST /login` validating user credentials against stored password hashes.

## Success Criteria
- **Passwords hashed before storage**: Raw passwords are never persisted in plaintext; hashed using `bcrypt` or salted `hashlib` SHA-256 prior to saving.
- **Login validates hashed password**: Authentication compares incoming plaintext credentials against stored hashes using timing-safe comparisons.

---

# Architecture & Implementation Specification

## 1. Overview
This module enhances the Task Manager backend with user authentication and registration workflows. It fulfills all requirements from the task scenario by implementing:
1. `User.register()`: Class and instance method to securely register accounts with validation and uniqueness enforcement.
2. `User.login()`: Class and instance method to authenticate users by validating hashed passwords.
3. Secure Password Hashing: Flexible support for `bcrypt` and standard library `hashlib` (SHA-256 with 16-byte random salt) using timing-attack resistant comparisons (`hmac.compare_digest`).
4. REST API Endpoints: Flask endpoints for registration (`/register`) and login (`/login`).
5. Comprehensive Test Suite: Test coverage for model methods, security guarantees, duplicate prevention, and HTTP endpoints.

## 2. Directory Structure

```text
practice/week-01-implement-user-registration-and-login-with-passw/
├── README.md       # Architecture specification and documentation
├── User.py         # User data model with register(), login(), and password hashing
├── Task.py         # Task model integrated with array-based storage
├── app.py          # Flask REST API containing /register and /login endpoints
└── test_auth.py    # Unit and integration test suite for auth & endpoints
```

## 3. Password Hashing Architecture

### 3.1 Salted Cryptographic Hashing (`hashlib` / `bcrypt`)
- **Zero Plaintext Storage**: When a user registers or updates their password, `User.hash_password(password)` is invoked immediately.
- **Cryptographic Salt**: When using `hashlib`, a unique 16-byte random salt (`os.urandom(16).hex()`) is generated for each password:
  ```text
  Format: sha256$<salt_32_hex_chars>$<digest_64_hex_chars>
  ```
- **Bcrypt Support**: If `bcrypt` is available or explicitly selected, bcrypt's adaptive key derivation function with cost factor is applied:
  ```text
  Format: $2b$12$...
  ```
- **Timing-Attack Resistance**: Verification uses `hmac.compare_digest` (or `bcrypt.checkpw`) to prevent timing attacks.

### 3.2 Success Criteria Verification
| Success Criterion | Implementation Mechanism | Validation in `test_auth.py` |
|---|---|---|
| **Passwords hashed before storage** | `User.set_password()` and `User.register()` call `hash_password()`; raw password is never assigned to `self.password_hash` or returned in serialized outputs. | `test_password_hashed_before_storage_on_init`, `test_password_hashed_before_storage_on_register`, `test_password_hash_salt_uniqueness` |
| **Login validates hashed password** | `User.login()` resolves user by username/email and executes `user.check_password(candidate_password)` against stored hash. | `test_login_validates_hashed_password_success`, `test_login_validates_hashed_password_wrong_password`, `test_login_with_nonexistent_user` |

---

## 4. API Reference

### 4.1 `User` Class (`User.py`)

| Member | Signature / Type | Description |
|---|---|---|
| `register(username, email, password, ...)` | `@classmethod` / function | Validates input, verifies uniqueness, hashes password, saves to registry, returns new `User`. |
| `login(username, password)` | `@classmethod` / function | Authenticates user credentials against stored password hash. Returns `User` on success, `None` on failure. |
| `hash_password(password, method=None)` | `@staticmethod -> str` | Hashes plaintext password using `bcrypt` or salted `hashlib` SHA-256. |
| `set_password(password, method=None)` | `Method -> None` | Hashes and stores the user password. |
| `check_password(password)` | `Method -> bool` | Constant-time verification of password against stored hash. |
| `tasks` | `List[Any]` | In-memory array storing user tasks. |
| `add_task(task)` | `Method -> Any` | Appends task to the user's task array. |
| `get_tasks()` | `Method -> List[Any]` | Retrieves array of user tasks. |
| `to_dict()` | `Method -> Dict[str, Any]` | Returns sanitized representation (excludes passwords). |

### 4.2 Flask Endpoints (`app.py`)

#### 1. Registration Endpoint
- **Route**: `POST /register`
- **Request Body**:
  ```json
  {
    "username": "sample_user",
    "email": "sample@example.com",
    "password": "SamplePassword123!"
  }
  ```
- **Responses**:
  - `201 Created`: User successfully registered.
    ```json
    {
      "message": "User registered successfully.",
      "user": {
        "id": 1,
        "username": "sample_user",
        "email": "sample@example.com",
        "tasks": [],
        "task_count": 0
      }
    }
    ```
  - `400 Bad Request`: Missing fields, invalid email format, empty password, or duplicate username/email.

#### 2. Login Endpoint
- **Route**: `POST /login`
- **Request Body**:
  ```json
  {
    "username": "sample_user",
    "password": "SamplePassword123!"
  }
  ```
- **Responses**:
  - `200 OK`: Valid credentials.
    ```json
    {
      "message": "Login successful.",
      "user": {
        "id": 1,
        "username": "sample_user",
        "email": "sample@example.com",
        "tasks": [],
        "task_count": 0
      }
    }
    ```
  - `401 Unauthorized`: Invalid username or password.
    ```json
    {
      "error": "Invalid username or password."
    }
    ```
  - `400 Bad Request`: Missing username or password.

---

## 5. Usage Example

```python
from User import User

# 1. Register new user (password is automatically hashed before storage)
user = User.register(
    username="john_doe",
    email="john@example.com",
    password="SuperSecurePassword123!"
)

print(user.password_hash)
# Output: sha256$8f92a...$d41d8... (raw password never stored)

# 2. Login with correct credentials
auth_user = User.login(username="john_doe", password="SuperSecurePassword123!")
assert auth_user is not None
print(f"Logged in as: {auth_user.username}")

# 3. Failed login attempt
failed_user = User.login(username="john_doe", password="WrongPassword")
assert failed_user is None
```

---

## 6. Testing

Run the test suite using `pytest`:

```bash
pytest practice/week-01-implement-user-registration-and-login-with-passw/test_auth.py -v
```

All test cases validate:
- User registration and duplicate prevention
- Password hashing and non-plaintext storage
- Successful and failed logins
- Sample users multi-account scenarios
- Flask API registration and login endpoints