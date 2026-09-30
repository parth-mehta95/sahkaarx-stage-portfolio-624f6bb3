"""
models.py - Domain Models for Task Manager Application.

Separation of Concerns:
This module contains the domain entities and in-memory persistence logic:
1. User class - Encapsulates user credentials, authentication logic, and task relationships.
2. Task class - Encapsulates task fields, status transitions, and serialization.
All validation and hashing routines are delegated to utils.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import uuid

from utils import (
    AuthenticationError,
    NotFoundError,
    UserAlreadyExistsError,
    ValidationError,
    hash_password,
    validate_email_format,
    validate_password_strength,
    validate_task_payload,
    validate_username,
    verify_password,
)


# =============================================================================
# Task Model
# =============================================================================

class Task:
    """
    Task domain entity representing a unit of work.

    Encapsulation:
    - Internal state managed via private attributes: _id, _title, _description, _status, _user_id, _created_at, _updated_at.
    - Controlled updates and validations.
    """

    _tasks_by_id: Dict[str, "Task"] = {}
    _id_counter: int = 0

    def __init__(
        self,
        title: str,
        description: str = "",
        status: str = "pending",
        user_id: Optional[Union[str, int]] = None,
        task_id: Optional[Union[str, int]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        """Initialize a new Task instance."""
        now = datetime.now(timezone.utc)

        if task_id is not None:
            self._id = str(task_id)
            try:
                numeric_val = int(task_id)
                if numeric_val > Task._id_counter:
                    Task._id_counter = numeric_val
            except (ValueError, TypeError):
                pass
        else:
            Task._id_counter += 1
            self._id = str(Task._id_counter)

        self._title = str(title).strip()
        self._description = str(description).strip() if description else ""
        self._status = str(status).strip().lower() if status else "pending"
        self._user_id = str(user_id) if user_id is not None else None
        self._created_at = created_at if created_at is not None else now
        self._updated_at = updated_at if updated_at is not None else now

        # Register in class storage
        Task._tasks_by_id[self._id] = self

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def id(self) -> str:
        """Encapsulated task ID."""
        return self._id

    @property
    def title(self) -> str:
        """Encapsulated task title."""
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        """Update task title with validation."""
        if not value or not str(value).strip():
            raise ValidationError("Task title cannot be empty.")
        self._title = str(value).strip()
        self._updated_at = datetime.now(timezone.utc)

    @property
    def description(self) -> str:
        """Encapsulated task description."""
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        """Update task description."""
        self._description = str(value).strip() if value else ""
        self._updated_at = datetime.now(timezone.utc)

    @property
    def status(self) -> str:
        """Encapsulated task status."""
        return self._status

    @status.setter
    def status(self, value: str) -> None:
        """Update task status with validation."""
        valid_statuses = {"pending", "in_progress", "completed"}
        val = str(value).strip().lower() if value else ""
        if val not in valid_statuses:
            raise ValidationError(f"Invalid status '{value}'. Allowed: {', '.join(sorted(valid_statuses))}.")
        self._status = val
        self._updated_at = datetime.now(timezone.utc)

    @property
    def user_id(self) -> Optional[str]:
        """Encapsulated user ID association."""
        return self._user_id

    @user_id.setter
    def user_id(self, value: Optional[Union[str, int]]) -> None:
        """Update associated user ID."""
        self._user_id = str(value) if value is not None else None
        self._updated_at = datetime.now(timezone.utc)

    @property
    def created_at(self) -> datetime:
        """Creation timestamp."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """Last updated timestamp."""
        return self._updated_at

    # -------------------------------------------------------------------------
    # Domain & Serialization Methods
    # -------------------------------------------------------------------------

    def update(self, **kwargs: Any) -> "Task":
        """
        Update multiple task attributes with validation.

        Args:
            **kwargs: Attributes to update (title, description, status, user_id).

        Returns:
            The updated Task instance.
        """
        validated = validate_task_payload(kwargs, require_title=False)

        if "title" in validated:
            self.title = validated["title"]
        if "description" in validated:
            self.description = validated["description"]
        if "status" in validated:
            self.status = validated["status"]
        if "user_id" in validated:
            self.user_id = validated["user_id"]

        self._updated_at = datetime.now(timezone.utc)
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert task instance to a clean JSON-serializable dictionary."""
        return {
            "id": self._id,
            "title": self._title,
            "description": self._description,
            "status": self._status,
            "user_id": self._user_id,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    # -------------------------------------------------------------------------
    # Class-Level Storage / Repository Operations
    # -------------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        title: str,
        description: str = "",
        status: str = "pending",
        user_id: Optional[Union[str, int]] = None,
        task_id: Optional[Union[str, int]] = None,
    ) -> "Task":
        """Validate payload and construct a new Task instance."""
        payload = {"title": title, "description": description, "status": status, "user_id": user_id}
        validated = validate_task_payload(payload, require_title=True)

        task = cls(
            title=validated["title"],
            description=validated.get("description", ""),
            status=validated.get("status", "pending"),
            user_id=validated.get("user_id"),
            task_id=task_id,
        )
        return task

    @classmethod
    def get_by_id(cls, task_id: Union[str, int]) -> Optional["Task"]:
        """Retrieve task by ID (string or integer)."""
        key = str(task_id)
        return cls._tasks_by_id.get(key)

    @classmethod
    def get_all(cls) -> List["Task"]:
        """Retrieve all stored tasks."""
        return list(cls._tasks_by_id.values())

    @classmethod
    def delete_by_id(cls, task_id: Union[str, int]) -> bool:
        """Delete task by ID from repository."""
        key = str(task_id)
        if key in cls._tasks_by_id:
            del cls._tasks_by_id[key]
            return True
        return False

    @classmethod
    def clear_all(cls) -> None:
        """Reset repository storage and ID counter."""
        cls._tasks_by_id.clear()
        cls._id_counter = 0


# =============================================================================
# User Model
# =============================================================================

class User:
    """
    User domain entity encapsulating authentication credentials, state, and tasks.

    OOP Principles Applied:
    1. Encapsulation:
       - Private attributes (_id, _username, _password_hash, _email, _created_at, _tasks)
       - Direct reading or modification of password hash is restricted.
    2. Delegation:
       - Password hashing and verification are delegated to utils.py.
       - Credential validation is delegated to utils.py.
    """

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
    ) -> None:
        """Direct constructor for User."""
        self._id = str(user_id) if user_id is not None else str(uuid.uuid4())
        self._username = str(username).strip()
        self._password_hash = str(password_hash)
        self._email = str(email).strip().lower() if email else ""
        self._created_at = created_at if created_at is not None else datetime.now(timezone.utc)
        self._tasks: Dict[str, Task] = {}

        # Register in class storage
        User._users_by_id[self._id] = self
        User._users_by_username[self._username.lower()] = self
        if self._email:
            User._users_by_email[self._email] = self

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def id(self) -> str:
        """Encapsulated user ID."""
        return self._id

    @property
    def username(self) -> str:
        """Encapsulated username."""
        return self._username

    @property
    def email(self) -> str:
        """Encapsulated email."""
        return self._email

    @property
    def created_at(self) -> datetime:
        """Account creation timestamp."""
        return self._created_at

    @property
    def password_hash(self) -> str:
        """Encapsulated password hash."""
        return self._password_hash

    # -------------------------------------------------------------------------
    # Authentication & Business Methods
    # -------------------------------------------------------------------------

    def check_password(self, password: str) -> bool:
        """Verify candidate plaintext password against stored hash."""
        return verify_password(password, self._password_hash)

    def create_task(self, title: str, description: str = "", status: str = "pending") -> Task:
        """Create and associate a task with this user."""
        task = Task.create(
            title=title,
            description=description,
            status=status,
            user_id=self._id,
        )
        self._tasks[task.id] = task
        return task

    def get_tasks(self) -> List[Task]:
        """Retrieve all tasks associated with this user."""
        # Sync with global task repo
        user_tasks = [t for t in Task.get_all() if t.user_id == self._id]
        return user_tasks

    def to_dict(self, include_tasks: bool = False) -> Dict[str, Any]:
        """
        Convert user entity to a safe JSON-serializable dictionary.
        Password hashes are never leaked in serialization.
        """
        data: Dict[str, Any] = {
            "id": self._id,
            "username": self._username,
            "email": self._email,
            "created_at": self._created_at.isoformat(),
        }
        if include_tasks:
            data["tasks"] = [t.to_dict() for t in self.get_tasks()]
        return data

    # -------------------------------------------------------------------------
    # Class-Level Factory & Repository Operations
    # -------------------------------------------------------------------------

    @classmethod
    def register(
        cls,
        username: str,
        password: str,
        email: str = "",
        user_id: Optional[Union[str, int]] = None,
    ) -> "User":
        """
        Validate credentials, hash password, and create a new registered User.

        Args:
            username: Desired username.
            password: Plaintext password.
            email: Optional email address.
            user_id: Optional custom user ID.

        Returns:
            Newly registered User instance.

        Raises:
            ValidationError: If inputs are invalid.
            UserAlreadyExistsError: If username or email is already taken.
        """
        clean_username = validate_username(username)
        validate_password_strength(password)
        clean_email = validate_email_format(email)

        # Check duplicate username
        if clean_username.lower() in cls._users_by_username:
            raise UserAlreadyExistsError(f"Username '{clean_username}' is already registered.")

        # Check duplicate email
        if clean_email and clean_email in cls._users_by_email:
            raise UserAlreadyExistsError(f"Email '{clean_email}' is already registered.")

        hashed = hash_password(password)
        user = cls(
            username=clean_username,
            password_hash=hashed,
            email=clean_email,
            user_id=user_id,
        )
        return user

    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional["User"]:
        """
        Authenticate a user by username and plaintext password.

        Args:
            username: Provided username.
            password: Provided plaintext password.

        Returns:
            The User instance if authenticated, or None if invalid credentials.
        """
        if not username or not password:
            return None

        clean_username = str(username).strip().lower()
        user = cls._users_by_username.get(clean_username)
        if user is None:
            return None

        if not user.check_password(password):
            return None

        return user

    @classmethod
    def get_by_id(cls, user_id: Union[str, int]) -> Optional["User"]:
        """Retrieve user by ID."""
        return cls._users_by_id.get(str(user_id))

    @classmethod
    def get_by_username(cls, username: str) -> Optional["User"]:
        """Retrieve user by username (case-insensitive)."""
        return cls._users_by_username.get(str(username).strip().lower())

    @classmethod
    def get_by_email(cls, email: str) -> Optional["User"]:
        """Retrieve user by email (case-insensitive)."""
        return cls._users_by_email.get(str(email).strip().lower())

    @classmethod
    def get_all(cls) -> List["User"]:
        """Retrieve all registered users."""
        return list(cls._users_by_id.values())

    @classmethod
    def clear_all(cls) -> None:
        """Clear all registered users from class storage."""
        cls._users_by_id.clear()
        cls._users_by_username.clear()
        cls._users_by_email.clear()
