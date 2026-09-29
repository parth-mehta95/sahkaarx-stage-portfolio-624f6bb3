# Refactor Authentication with OOP Principles

## Task Brief
Refactor your login/registration logic to use User class methods; apply encapsulation to password handling.

## Scenario
Refactor your authentication code to use User class methods instead of inline route logic for better maintainability.

## Deliverables
- User class with `authenticate()` method
- User class with `register()` method
- Refactored Flask authentication routes delegating to User methods
- Test suite verifying authentication flow and encapsulation

## Success Criteria
- Authentication logic encapsulated in User class
- Routes delegate to User methods
- Password hashing still applied correctly and plaintext passwords never stored or exposed

---

## 1. Architectural Overview & OOP Principles

### The Problem: Procedural Inline Logic in Routes
In procedural Flask applications, routes often handle request validation, database lookups, manual password hashing, and error response formatting directly inside route handler functions. This violates several core software engineering principles:
- **Tight Coupling**: Route handlers are tightly coupled to specific hashing and database implementations.
- **Code Duplication**: Authentication and password checks cannot be reused by CLI commands, background workers, or other API endpoints.
- **Security Leak Risk**: Without encapsulation, sensitive attributes like plaintext passwords or raw hashes can accidentally be serialized into API responses or logged.

### The Solution: Object-Oriented Refactoring
By applying Object-Oriented Programming (OOP) principles, authentication logic is moved into domain methods on the `User` class:

```
+-------------------------------------------------------------+
|                      Flask HTTP Routes                      |
|                  (routes.py / Blueprint)                    |
+------------------------------+------------------------------+
                               |
            Delegates HTTP     |     Delegates HTTP
            POST /register     |     POST /login
                               v
+-------------------------------------------------------------+
|                         User Model                          |
|                        (models.py)                          |
+-------------------------------------------------------------+
|  Class Methods:                                             |
|    - User.register(username, password, email)               |
|        -> Validates input, hashes password, saves instance  |
|    - User.authenticate(username, password)                  |
|        -> Retrieves user, timing-safe hash comparison       |
|                                                             |
|  Encapsulated Attributes:                                   |
|    - _id, _username, _password_hash, _email, _tasks         |
|                                                             |
|  Encapsulated Security:                                     |
|    - @property password: raises AttributeError on read      |
|    - user.verify_password(plaintext) -> bool                |
|    - user.to_dict() -> never exposes password_hash          |
+-------------------------------------------------------------+
```

### Core OOP Principles Applied

1. **Encapsulation**:
   - Private attributes (`_id`, `_username`, `_password_hash`, `_email`) protect internal object state from unauthorized external modification.
   - Plaintext passwords are **never stored**; only cryptographic salted hashes are held in `_password_hash`.
   - Accessing `user.password` directly raises an `AttributeError`, preventing accidental leaks.
   - Serialized dictionaries (`user.to_dict()`) strip all sensitive authentication hashes.

2. **Delegation**:
   - The Flask route handlers do not execute inline password hashing or lookup queries.
   - `POST /register` delegates the entire creation, validation, and hashing pipeline to `User.register()`.
   - `POST /login` delegates credential lookup and verification directly to `User.authenticate()`.

3. **Single Responsibility Principle (SRP)**:
   - `routes.py` is responsible solely for HTTP transport concerns (extracting request payloads, choosing HTTP status codes, and formatting JSON responses).
   - `models.py` (`User`) is responsible for user identity, authentication logic, credential hashing, and state persistence.

---

## 2. Minimum Artifacts Summary

| Artifact | Location | Purpose |
| :--- | :--- | :--- |
| **`models.py`** | [`models.py`](file:///d:/challengers%20testing/sahkaarx-stage-portfolio-624f6bb3/practice/week-03-refactor-authentication-with-oop-principles/models.py) | User class with `authenticate()` and `register()` class methods, private attributes, and Task model |
| **`routes.py`** | [`routes.py`](file:///d:/challengers%20testing/sahkaarx-stage-portfolio-624f6bb3/practice/week-03-refactor-authentication-with-oop-principles/routes.py) | Flask routes delegating `/register` and `/login` to User class methods |
| **`app.py`** | [`app.py`](file:///d:/challengers%20testing/sahkaarx-stage-portfolio-624f6bb3/practice/week-03-refactor-authentication-with-oop-principles/app.py) | Application entrypoint and factory runner |
| **`test_auth.py`** | [`test_auth.py`](file:///d:/challengers%20testing/sahkaarx-stage-portfolio-624f6bb3/practice/week-03-refactor-authentication-with-oop-principles/test_auth.py) | Unit & integration test suite verifying OOP methods and HTTP routes |

---

## 3. User Class Implementation Details (`models.py`)

### `User.register(username, password, email="")` Class Method
```python
@classmethod
def register(
    cls,
    username: str,
    password: str,
    email: str = "",
    user_id: Optional[Union[str, int]] = None,
    *args: Any,
    **kwargs: Any,
) -> "User":
    """
    Class method to validate, hash password, instantiate, and register a new User.
    Enforces uniqueness, runs input validations, and securely hashes password.
    """
    # 1. Input Validation
    if not username or not str(username).strip():
        raise ValidationError("Username is required and cannot be empty.")
    if len(str(username).strip()) < 3:
        raise ValidationError("Username must be at least 3 characters long.")
    if not password or len(str(password)) < 4:
        raise ValidationError("Password must be at least 4 characters long.")

    # 2. Uniqueness Checks
    clean_username = str(username).strip()
    if cls.exists(clean_username):
        raise UserAlreadyExistsError(f"Username '{clean_username}' is already registered.")

    # 3. Secure Salted Hashing
    pwhash = generate_password_hash(str(password))

    # 4. Instantiate & Register
    user = cls(
        username=clean_username,
        password_hash=pwhash,
        email=str(email).strip().lower() if email else "",
        user_id=user_id,
    )
    return user
```

### `User.authenticate(username, password)` Method
```python
@classmethod
def authenticate(
    cls,
    username: str,
    password: str,
) -> Optional["User"]:
    """
    Authenticate user credentials by username and plaintext password.
    
    Returns:
        User: The authenticated User object if credentials match.
        None: If user does not exist or password is invalid.
    """
    if not username or not password:
        return None

    clean_username = str(username).strip()
    user = cls.get_by_username(clean_username)
    if user is None:
        return None

    # Timing-safe cryptographic hash comparison
    if user.verify_password(str(password)):
        return user

    return None
```

---

## 4. Refactored Flask Routes (`routes.py`)

### Registration Route (`POST /register`)
```python
@auth_bp.route("/register", methods=["POST"])
def register():
    data = get_request_data()
    username = data.get("username")
    password = data.get("password")
    email = data.get("email", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required.", "status_code": 400}), 400

    try:
        # DELEGATION: User class method encapsulates validation, hashing, and persistence
        user = User.register(username=username, password=password, email=email)
        return jsonify({
            "message": "User registered successfully.",
            "user": user.to_dict(),
            "status_code": 201,
        }), 201
    except UserAlreadyExistsError as e:
        return jsonify({"error": str(e), "status_code": 409}), 409
    except ValidationError as e:
        return jsonify({"error": str(e), "status_code": 400}), 400
```

### Login Route (`POST /login`)
```python
@auth_bp.route("/login", methods=["POST"])
def login():
    data = get_request_data()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required.", "status_code": 400}), 400

    # DELEGATION: User class encapsulates lookup and hash comparison
    user = User.authenticate(username=username, password=password)

    if user is None:
        return jsonify({"error": "Invalid username or password.", "status_code": 401}), 401

    return jsonify({
        "message": "Login successful.",
        "user": user.to_dict(),
        "status_code": 200,
    }), 200
```

---

## 5. Endpoints Reference & Status Codes

| HTTP Method | Route | Status Code | Description |
| :--- | :--- | :--- | :--- |
| **POST** | `/register` or `/auth/register` | `201 Created` | Registers a new user via `User.register()` |
| **POST** | `/register` or `/auth/register` | `400 Bad Request` | Missing required parameters or failed validation |
| **POST** | `/register` or `/auth/register` | `409 Conflict` | Username or email already registered |
| **POST** | `/login` or `/auth/login` | `200 OK` | Authenticates credentials via `User.authenticate()` |
| **POST** | `/login` or `/auth/login` | `400 Bad Request` | Missing username or password |
| **POST** | `/login` or `/auth/login` | `401 Unauthorized` | Invalid username or incorrect password |
| **GET** | `/users` | `200 OK` | Retrieves all users (sanitized, hashes hidden) |
| **GET** | `/users/<username>` | `200 OK` / `404` | Retrieves single user by username |
| **POST** | `/logout` | `200 OK` | Ends user session |

---

## 6. Sample Requests & Responses

### 1. Register User (`POST /register`)
**Request:**
```bash
curl -X POST http://127.0.0.1:5000/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "SuperSecretPass123", "email": "alice@example.com"}'
```

**Response (`201 Created`):**
```json
{
  "message": "User registered successfully.",
  "user": {
    "id": "e98e21a2-581d-44a6-89ce-38d5e1ecdf31",
    "username": "alice",
    "email": "alice@example.com",
    "task_count": 0,
    "created_at": "2026-09-29T12:15:00+00:00"
  },
  "status_code": 201
}
```

### 2. Login User (`POST /login`)
**Request:**
```bash
curl -X POST http://127.0.0.1:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "SuperSecretPass123"}'
```

**Response (`200 OK`):**
```json
{
  "message": "Login successful.",
  "user": {
    "id": "e98e21a2-581d-44a6-89ce-38d5e1ecdf31",
    "username": "alice",
    "email": "alice@example.com",
    "task_count": 0,
    "created_at": "2026-09-29T12:15:00+00:00"
  },
  "status_code": 200
}
```

### 3. Invalid Login (`POST /login` with incorrect password)
**Request:**
```bash
curl -X POST http://127.0.0.1:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "WrongPassword"}'
```

**Response (`401 Unauthorized`):**
```json
{
  "error": "Invalid username or password.",
  "status_code": 401
}
```

---

## 7. Running Tests & Verification

Execute the automated test suite covering all deliverables and success criteria:

```bash
python -m unittest test_auth.py
```

### Expected Output:
```
...............
----------------------------------------------------------------------
Ran 15 tests in 0.082s

OK
```

All 15 tests cover:
- `User.register()`: Creation, input validation, salted hashing, duplicate prevention.
- `User.authenticate()`: Matching credentials, mismatched passwords, unknown usernames.
- Encapsulation: `user.password` read protection, property setters, and hash exclusion in `to_dict()`.
- Routes: `POST /register` (`201`, `400`, `409`) and `POST /login` (`200`, `400`, `401`).