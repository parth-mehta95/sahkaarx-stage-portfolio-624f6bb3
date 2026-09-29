"""
models.py - Domain Models with OOP Principles and Encapsulated Authentication.

Deliverables:
- User class with authenticate(username, password) method
- User class with register(username, password) class method
- Encapsulated password hashing and attribute access (_id, _username, _password_hash, etc.)
- Reusable Task model with encapsulation and user association
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

# Secure password hashing with fallback to hashlib PBKDF2
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
# Custom Domain Exceptions
# =============================================================================

class AuthenticationError(Exception):
    """Raised when authentication credentials fail validation."""
    pass


class UserAlreadyExistsError(ValueError):
    """Raised when attempting to register a username or email that already exists."""
    pass


class ValidationError(ValueError):
    """Raised when input validation fails (e.g., blank username or weak password)."""
    pass


# =============================================================================
# User Class (Encapsulated Authentication & OOP Principles)
# =============================================================================

class User:
    """
    User entity encapsulating authentication logic, credentials, and state.

    OOP Principles Applied:
    1. Encapsulation:
       - Private attributes (_id, _username, _password_hash, _email, _tasks)
       - Password plaintext is NEVER stored; only salted cryptographic hashes
       - Direct reading of user.password is disallowed (raises AttributeError)
    2. Delegation:
       - Password verification delegated to verify_password()
       - User creation and validation encapsulated inside User.register()
       - Credential validation and authentication encapsulated inside User.authenticate()
    3. Single Responsibility Principle (SRP):
       - User manages user identity, credentials, and associated tasks
       - Routes merely delegate requests to User domain methods
    """

    # Class-level user registry / repository
    _users_by_id: Dict[str, "User"] = {}
    _users_by_username: Dict[str, "User"] = {}
    _users_by_email: Dict[str, "User"] = {}

    def __init__(
        self,
        username: str,
        password_hash: str,
        email: str = "",
        user_id: Optional[Union[str, int]] = None,
        created_at: Optional[datetime] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Direct constructor for User.

        Note: Applications should prefer `User.register(username, password)`
        which enforces validation, uniqueness checks, and hashing.
        """
        if not username or not str(username).strip():
            raise ValidationError("Username cannot be empty.")
        if not password_hash:
            raise ValidationError("Password hash is required.")

        self._id: str = str(user_id) if user_id is not None else str(uuid.uuid4())
        self._username: str = str(username).strip()
        self._password_hash: str = str(password_hash)
        self._email: str = str(email).strip().lower() if email else ""
        self._created_at: datetime = created_at if created_at is not None else datetime.now(timezone.utc)
        self._tasks: Dict[str, "Task"] = {}

        # Register in class storage
        User._users_by_id[self._id] = self
        User._users_by_username[self._username.lower()] = self
        if self._email:
            User._users_by_email[self._email] = self

    # -------------------------------------------------------------------------
    # Properties (Encapsulation of Private Attributes)
    # -------------------------------------------------------------------------

    @property
    def id(self) -> str:
        """Get encapsulated private user ID."""
        return self._id

    @property
    def username(self) -> str:
        """Get encapsulated private username."""
        return self._username

    @property
    def name(self) -> str:
        """Alias for username."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """Update username with validation."""
        clean = str(value or "").strip()
        if not clean:
            raise ValidationError("Username cannot be empty.")
        if len(clean) < 3:
            raise ValidationError("Username must be at least 3 characters long.")

        # If changing username, update class registry
        old_key = self._username.lower()
        new_key = clean.lower()
        if new_key != old_key and new_key in User._users_by_username:
            raise UserAlreadyExistsError(f"Username '{clean}' is already taken.")

        if old_key in User._users_by_username:
            del User._users_by_username[old_key]

        self._username = clean
        User._users_by_username[new_key] = self

    @property
    def email(self) -> str:
        """Get encapsulated private email."""
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        """Update email with validation."""
        clean = str(value or "").strip().lower()
        if clean and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValidationError(f"Invalid email format: '{value}'")

        old_key = self._email
        if old_key and old_key in User._users_by_email:
            del User._users_by_email[old_key]

        self._email = clean
        if clean:
            User._users_by_email[clean] = self

    @property
    def password_hash(self) -> str:
        """Get the stored cryptographic password hash."""
        return self._password_hash

    @property
    def password(self) -> str:
        """
        Security Encapsulation: Plaintext password is NEVER accessible.
        Attempting to read `user.password` raises AttributeError.
        """
        raise AttributeError(
            "Plaintext password is private and not readable. "
            "Use user.verify_password(password) to check credentials."
        )

    @password.setter
    def password(self, plaintext: str) -> None:
        """
        Encapsulated password setter: Automatically hashes the plaintext.
        Plaintext is never stored.
        """
        self.set_password(plaintext)

    @property
    def created_at(self) -> datetime:
        """Get user creation timestamp."""
        return self._created_at

    @property
    def tasks(self) -> List["Task"]:
        """Get list of tasks associated with this user."""
        return list(self._tasks.values())

    # -------------------------------------------------------------------------
    # Password & Credential Verification Methods
    # -------------------------------------------------------------------------

    def set_password(self, plaintext: str) -> None:
        """
        Hash plaintext password and update the encapsulated _password_hash.

        Args:
            plaintext: Plaintext password string.
        """
        if not plaintext or len(str(plaintext)) < 4:
            raise ValidationError("Password must be at least 4 characters long.")
        self._password_hash = generate_password_hash(str(plaintext))

    def verify_password(self, plaintext: str) -> bool:
        """
        Verify candidate plaintext password against stored cryptographic hash.

        Args:
            plaintext: Candidate plaintext password.

        Returns:
            bool: True if password matches, False otherwise.
        """
        if not plaintext or not self._password_hash:
            return False
        return check_password_hash(self._password_hash, str(plaintext))

    def check_password(self, plaintext: str) -> bool:
        """Alias for verify_password."""
        return self.verify_password(plaintext)

    # -------------------------------------------------------------------------
    # Deliverable 1: User Class authenticate() Method
    # -------------------------------------------------------------------------

    @classmethod
    def authenticate(
        cls,
        username: str,
        password: str,
    ) -> Optional["User"]:
        """
        Authenticate user credentials by username and plaintext password.

        Encapsulates authentication logic:
        1. Validates inputs are non-empty strings.
        2. Retrieves user record from repository by username.
        3. Verifies password using secure cryptographic hash comparison.
        4. Returns User instance on success, or None on failure.

        Args:
            username: The user's registered username.
            password: The plaintext candidate password.

        Returns:
            User: The authenticated User object if credentials are valid.
            None: If user does not exist or password does not match.

        Example:
            user = User.authenticate("alice", "secret123")
            if user:
                print(f"Logged in as {user.username}")
        """
        if not username or not password:
            return None

        clean_username = str(username).strip()
        user = cls.get_by_username(clean_username)
        if user is None:
            return None

        if user.verify_password(str(password)):
            return user

        return None

    # Support instance-level authentication as well: user.authenticate(password)
    def authenticate_instance(self, password: str) -> bool:
        """Verify instance password directly."""
        return self.verify_password(password)

    # -------------------------------------------------------------------------
    # Deliverable 2: User Class register() Class Method
    # -------------------------------------------------------------------------

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

        Encapsulates registration logic:
        1. Validates username presence, length, and format.
        2. Validates password strength (minimum length).
        3. Enforces uniqueness across usernames and emails.
        4. Cryptographically hashes plaintext password using secure salt.
        5. Instantiates and registers new User object.
        6. Returns the newly registered User instance.

        Args:
            username: Desired unique username.
            password: Plaintext password (will be hashed).
            email: Optional email address.
            user_id: Optional custom identifier.

        Returns:
            User: The newly created and registered User instance.

        Raises:
            ValidationError: If username or password fail validation.
            UserAlreadyExistsError: If username or email is already taken.

        Example:
            new_user = User.register("alice", "securepass123", email="alice@example.com")
        """
        # 1. Validation
        if not username or not str(username).strip():
            raise ValidationError("Username is required and cannot be empty.")

        clean_username = str(username).strip()
        if len(clean_username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")

        if not password or not str(password):
            raise ValidationError("Password is required and cannot be empty.")

        if len(str(password)) < 4:
            raise ValidationError("Password must be at least 4 characters long.")

        clean_email = str(email or kwargs.get("email", "")).strip().lower()
        if clean_email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean_email):
            raise ValidationError(f"Invalid email format: '{clean_email}'")

        # 2. Uniqueness Checks
        if cls.exists(clean_username):
            raise UserAlreadyExistsError(f"Username '{clean_username}' is already registered.")

        if clean_email and clean_email in cls._users_by_email:
            raise UserAlreadyExistsError(f"Email '{clean_email}' is already registered.")

        # 3. Secure Password Hashing
        pwhash = generate_password_hash(str(password))

        # 4. Instantiate & Register
        resolved_id = user_id if user_id is not None else kwargs.get("id")
        user = cls(
            username=clean_username,
            password_hash=pwhash,
            email=clean_email,
            user_id=resolved_id,
        )
        return user

    # -------------------------------------------------------------------------
    # Query & Registry Class Methods
    # -------------------------------------------------------------------------

    @classmethod
    def get_by_id(cls, user_id: Union[str, int]) -> Optional["User"]:
        """Retrieve a User by unique ID."""
        return cls._users_by_id.get(str(user_id))

    @classmethod
    def get_by_username(cls, username: str) -> Optional["User"]:
        """Retrieve a User by username (case-insensitive)."""
        if not username:
            return None
        return cls._users_by_username.get(str(username).strip().lower())

    @classmethod
    def get_by_email(cls, email: str) -> Optional["User"]:
        """Retrieve a User by email (case-insensitive)."""
        if not email:
            return None
        return cls._users_by_email.get(str(email).strip().lower())

    @classmethod
    def exists(cls, username: str) -> bool:
        """Check if a username is already registered."""
        return str(username).strip().lower() in cls._users_by_username

    @classmethod
    def get_all(cls) -> List["User"]:
        """Retrieve all registered users."""
        return list(cls._users_by_id.values())

    @classmethod
    def delete_by_id(cls, user_id: Union[str, int]) -> bool:
        """Remove a user from the registry."""
        user = cls.get_by_id(user_id)
        if user is None:
            return False

        uid = str(user.id)
        uname = user.username.lower()
        uemail = user.email.lower()

        if uid in cls._users_by_id:
            del cls._users_by_id[uid]
        if uname in cls._users_by_username:
            del cls._users_by_username[uname]
        if uemail and uemail in cls._users_by_email:
            del cls._users_by_email[uemail]

        return True

    @classmethod
    def clear_all(cls) -> None:
        """Reset registry (used between tests)."""
        cls._users_by_id.clear()
        cls._users_by_username.clear()
        cls._users_by_email.clear()
        Task.clear_all()

    # -------------------------------------------------------------------------
    # Task Management on User
    # -------------------------------------------------------------------------

    def create_task(
        self,
        title: str,
        description: str = "",
        status: str = "pending",
        task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> "Task":
        """Create and associate a Task with this User."""
        task = Task.create(
            title=title,
            description=description,
            status=status,
            user_id=self._id,
            task_id=task_id,
            **kwargs,
        )
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Optional["Task"]:
        """Retrieve an associated task by ID."""
        return self._tasks.get(str(task_id))

    def get_all_tasks(self) -> List["Task"]:
        """Retrieve all tasks associated with this user."""
        return list(self._tasks.values())

    def delete_task(self, task_id: str) -> bool:
        """Disassociate and delete a task."""
        tid = str(task_id)
        if tid in self._tasks:
            del self._tasks[tid]
            Task.delete_by_id(tid)
            return True
        return False

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self, include_tasks: bool = False) -> Dict[str, Any]:
        """
        Serialize user to dictionary format.
        Encapsulation guarantee: Password hash is NEVER exposed in the public dict.
        """
        data: Dict[str, Any] = {
            "id": self._id,
            "username": self._username,
            "email": self._email,
            "task_count": len(self._tasks),
            "created_at": self._created_at.isoformat(),
        }
        if include_tasks:
            data["tasks"] = [t.to_dict() for t in self._tasks.values()]
        return data

    def __repr__(self) -> str:
        return f"<User id='{self._id}' username='{self._username}'>"


# =============================================================================
# Task Model (Encapsulated Task Entity)
# =============================================================================

class Task:
    """
    Task entity encapsulating task state, ownership, and operations.
    """
    _registry: Dict[str, "Task"] = {}

    def __init__(
        self,
        title: str,
        description: str = "",
        status: str = "pending",
        completed: bool = False,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        id: Optional[str] = None,
        name: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        resolved_title = title or name or kwargs.get("title") or kwargs.get("name") or ""
        if not resolved_title:
            raise ValidationError("Task title cannot be empty.")

        resolved_id = task_id if task_id is not None else id
        if resolved_id is None:
            resolved_id = kwargs.get("task_id") or kwargs.get("id") or str(uuid.uuid4())

        self._id: str = str(resolved_id)
        self._title: str = str(resolved_title).strip()
        self._description: str = str(description or kwargs.get("description", "")).strip()
        self._status: str = str(status or kwargs.get("status", "pending"))
        self._completed: bool = bool(completed or self._status.lower() == "completed")
        self._user_id: Optional[str] = str(user_id) if user_id is not None else kwargs.get("user_id")
        self._created_at: datetime = datetime.now(timezone.utc)
        self._updated_at: datetime = datetime.now(timezone.utc)

        Task._registry[self._id] = self

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        clean = str(value or "").strip()
        if not clean:
            raise ValidationError("Task title cannot be empty.")
        self._title = clean
        self._updated_at = datetime.now(timezone.utc)

    @property
    def name(self) -> str:
        """Alias for title."""
        return self._title

    @name.setter
    def name(self, value: str) -> None:
        self.title = value

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = str(value or "").strip()
        self._updated_at = datetime.now(timezone.utc)

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, value: str) -> None:
        self._status = str(value or "pending")
        self._completed = self._status.lower() == "completed"
        self._updated_at = datetime.now(timezone.utc)

    @property
    def completed(self) -> bool:
        return self._completed

    @completed.setter
    def completed(self, value: bool) -> None:
        self._completed = bool(value)
        self._status = "completed" if self._completed else "pending"
        self._updated_at = datetime.now(timezone.utc)

    @property
    def user_id(self) -> Optional[str]:
        return self._user_id

    @user_id.setter
    def user_id(self, value: Optional[str]) -> None:
        self._user_id = str(value) if value is not None else None
        self._updated_at = datetime.now(timezone.utc)

    # -------------------------------------------------------------------------
    # Task Operations
    # -------------------------------------------------------------------------

    def mark_completed(self) -> None:
        """Mark task as completed."""
        self.completed = True

    def update(self, **kwargs: Any) -> "Task":
        """Update multiple task attributes with validation."""
        if "title" in kwargs:
            self.title = kwargs["title"]
        elif "name" in kwargs:
            self.name = kwargs["name"]

        if "description" in kwargs:
            self.description = kwargs["description"]

        if "completed" in kwargs:
            self.completed = kwargs["completed"]
        elif "status" in kwargs:
            self.status = kwargs["status"]

        if "user_id" in kwargs:
            self.user_id = kwargs["user_id"]

        self._updated_at = datetime.now(timezone.utc)
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return {
            "id": self._id,
            "title": self._title,
            "name": self._title,
            "description": self._description,
            "status": self._status,
            "completed": self._completed,
            "user_id": self._user_id,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    # -------------------------------------------------------------------------
    # Class Methods
    # -------------------------------------------------------------------------

    @classmethod
    def create(cls, title: str, **kwargs: Any) -> "Task":
        """Class factory method for creating Task instances."""
        return cls(title=title, **kwargs)

    @classmethod
    def get_by_id(cls, task_id: Union[str, int]) -> Optional["Task"]:
        """Retrieve task by unique identifier."""
        return cls._registry.get(str(task_id))

    @classmethod
    def get_all(cls) -> List["Task"]:
        """Retrieve all registered tasks."""
        return list(cls._registry.values())

    @classmethod
    def delete_by_id(cls, task_id: Union[str, int]) -> bool:
        """Delete task from registry."""
        tid = str(task_id)
        if tid in cls._registry:
            del cls._registry[tid]
            return True
        return False

    @classmethod
    def clear_all(cls) -> None:
        """Reset task registry."""
        cls._registry.clear()

    def __repr__(self) -> str:
        return f"<Task id='{self._id}' title='{self._title}' status='{self._status}'>"
