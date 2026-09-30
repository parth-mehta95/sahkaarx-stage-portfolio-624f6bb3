"""
models.py - Fully Type-Hinted Domain Models for Task Manager Application.

Deliverables:
- Type-hinted models with comprehensive typing annotations
- User domain entity with credential management, encapsulation, and relationships
- Task domain entity with status management, validation, and serialization
- In-memory thread-safe class repository persistence methods
"""

from __future__ import annotations

from datetime import datetime, timezone
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure current directory is in sys.path for direct and modular execution
current_dir: str = str(Path(__file__).resolve().parent)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from utils import (
        AuthenticationError,
        NotFoundError,
        UserAlreadyExistsError,
        ValidationError,
        hash_password,
        validate_email_format,
        validate_password_strength,
        validate_task_payload,
        validate_task_status,
        validate_username,
        verify_password,
    )
except ImportError:  # pragma: no cover
    from .utils import (
        AuthenticationError,
        NotFoundError,
        UserAlreadyExistsError,
        ValidationError,
        hash_password,
        validate_email_format,
        validate_password_strength,
        validate_task_payload,
        validate_task_status,
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
    - Internal state managed via private attributes: _id, _title, _description,
      _status, _completed, _user_id, _created_at, _updated_at.
    - Type-annotated getters and setters enforce domain invariants.
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
        completed: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        """Initialize a new Task instance with explicit type hints."""
        now: datetime = datetime.now(timezone.utc)

        if task_id is not None:
            self._id: str = str(task_id)
            try:
                numeric_val: int = int(task_id)
                if numeric_val > Task._id_counter:
                    Task._id_counter = numeric_val
            except (ValueError, TypeError):
                pass
        else:
            Task._id_counter += 1
            self._id = str(Task._id_counter)

        self._title: str = str(title).strip()
        self._description: str = str(description).strip() if description else ""
        norm_status: str = validate_task_status(status) if status else "pending"
        self._status: str = norm_status
        self._completed: bool = completed or (self._status == "completed")
        if self._completed:
            self._status = "completed"

        self._user_id: Optional[str] = str(user_id) if user_id is not None else None
        self._created_at: datetime = created_at if created_at is not None else now
        self._updated_at: datetime = updated_at if updated_at is not None else now

        # Register in class storage
        Task._tasks_by_id[self._id] = self

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def id(self) -> str:
        """Encapsulated unique task ID."""
        return self._id

    @property
    def title(self) -> str:
        """Encapsulated task title."""
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        """Update task title with non-empty validation."""
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
        """Encapsulated task status string."""
        return self._status

    @status.setter
    def status(self, value: str) -> None:
        """Update task status with domain vocabulary validation."""
        normalized: str = validate_task_status(value)
        self._status = normalized
        self._completed = (normalized == "completed")
        self._updated_at = datetime.now(timezone.utc)

    @property
    def completed(self) -> bool:
        """Boolean completion status flag."""
        return self._completed

    @completed.setter
    def completed(self, value: bool) -> None:
        """Update completion status boolean and sync status text."""
        self._completed = bool(value)
        if self._completed:
            self._status = "completed"
        elif self._status == "completed":
            self._status = "pending"
        self._updated_at = datetime.now(timezone.utc)

    @property
    def user_id(self) -> Optional[str]:
        """Encapsulated user ID owning this task."""
        return self._user_id

    @user_id.setter
    def user_id(self, value: Optional[Union[str, int]]) -> None:
        """Update owner user ID."""
        self._user_id = str(value) if value is not None else None
        self._updated_at = datetime.now(timezone.utc)

    @property
    def created_at(self) -> datetime:
        """Task creation timestamp."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """Task last updated timestamp."""
        return self._updated_at

    # -------------------------------------------------------------------------
    # State Transitions & Methods
    # -------------------------------------------------------------------------

    def update(self, **kwargs: Any) -> None:
        """
        Update multiple task attributes with validation.

        Args:
            **kwargs: Dictionary of fields to update ('title', 'description', 'status', 'completed', 'user_id').
        """
        validated: Dict[str, Any] = validate_task_payload(kwargs, require_title=False)

        if "title" in validated:
            self.title = validated["title"]
        if "description" in validated:
            self.description = validated["description"]
        if "status" in validated:
            self.status = validated["status"]
        if "completed" in validated:
            self.completed = validated["completed"]
        if "user_id" in validated:
            self.user_id = validated["user_id"]

        self._updated_at = datetime.now(timezone.utc)

    def mark_completed(self) -> None:
        """Mark task as completed and update timestamps."""
        self._status = "completed"
        self._completed = True
        self._updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize task entity to dictionary representation."""
        return {
            "id": self._id,
            "title": self._title,
            "description": self._description,
            "status": self._status,
            "completed": self._completed,
            "user_id": self._user_id,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        """String representation of Task."""
        return f"<Task id={self._id!r} title={self._title!r} status={self._status!r}>"

    # -------------------------------------------------------------------------
    # In-Memory Repository Persistence Operations
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
        payload: Dict[str, Any] = {
            "title": title,
            "description": description,
            "status": status,
            "user_id": user_id,
        }
        validated: Dict[str, Any] = validate_task_payload(payload, require_title=True)

        task: Task = cls(
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
        key: str = str(task_id)
        return cls._tasks_by_id.get(key)

    @classmethod
    def get_all(cls) -> List["Task"]:
        """Retrieve all stored tasks."""
        return list(cls._tasks_by_id.values())

    @classmethod
    def filter_by(
        cls,
        user_id: Optional[Union[str, int]] = None,
        status: Optional[str] = None,
    ) -> List["Task"]:
        """Retrieve tasks matching optional user_id and status filters."""
        tasks: List[Task] = list(cls._tasks_by_id.values())
        if user_id is not None:
            tasks = [t for t in tasks if t.user_id == str(user_id)]
        if status is not None:
            norm_status: str = validate_task_status(status)
            tasks = [t for t in tasks if t.status == norm_status]
        return tasks

    @classmethod
    def delete_by_id(cls, task_id: Union[str, int]) -> bool:
        """Delete task by ID from repository."""
        key: str = str(task_id)
        if key in cls._tasks_by_id:
            del cls._tasks_by_id[key]
            return True
        return False

    @classmethod
    def clear_all(cls) -> None:
        """Clear all tasks and reset counter (useful for test isolation)."""
        cls._tasks_by_id.clear()
        cls._id_counter = 0


# =============================================================================
# User Model
# =============================================================================

class User:
    """
    User domain entity representing an application user.

    Encapsulation:
    - Internal state managed via private attributes: _id, _username, _email,
      _password_hash, _created_at.
    - Password hashing and authentication logic encapsulated within class methods.
    - User-to-Task relationships maintained via domain queries.
    """

    _users_by_id: Dict[str, "User"] = {}
    _users_by_username: Dict[str, "User"] = {}
    _users_by_email: Dict[str, "User"] = {}
    _id_counter: int = 0

    def __init__(
        self,
        username: str,
        email: str,
        password_hash: str,
        user_id: Optional[Union[str, int]] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        """Initialize a new User instance with type-hinted parameters."""
        now: datetime = datetime.now(timezone.utc)

        if user_id is not None:
            self._id: str = str(user_id)
            try:
                numeric_val: int = int(user_id)
                if numeric_val > User._id_counter:
                    User._id_counter = numeric_val
            except (ValueError, TypeError):
                pass
        else:
            User._id_counter += 1
            self._id = str(User._id_counter)

        self._username: str = validate_username(username)
        self._email: str = validate_email_format(email)
        self._password_hash: str = password_hash
        self._created_at: datetime = created_at if created_at is not None else now

        # Register in class storage
        User._users_by_id[self._id] = self
        User._users_by_username[self._username.lower()] = self
        User._users_by_email[self._email.lower()] = self

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
    def password_hash(self) -> str:
        """Encapsulated password hash."""
        return self._password_hash

    @property
    def created_at(self) -> datetime:
        """User registration timestamp."""
        return self._created_at

    # -------------------------------------------------------------------------
    # Authentication & Relationship Logic
    # -------------------------------------------------------------------------

    def check_password(self, candidate_password: str) -> bool:
        """Verify candidate plaintext password against stored hash."""
        return verify_password(candidate_password, self._password_hash)

    def set_password(self, new_password: str) -> None:
        """Update user password with validation and cryptographic hashing."""
        validate_password_strength(new_password)
        self._password_hash = hash_password(new_password)

    def get_tasks(self) -> List[Task]:
        """Retrieve all tasks assigned to or created by this user."""
        return Task.filter_by(user_id=self._id)

    def create_task(
        self,
        title: str,
        description: str = "",
        status: str = "pending",
    ) -> Task:
        """Create and associate a new Task with this user."""
        return Task.create(
            title=title,
            description=description,
            status=status,
            user_id=self._id,
        )

    def to_dict(self, include_tasks: bool = False) -> Dict[str, Any]:
        """
        Serialize user entity to dictionary representation.
        Safely excludes cryptographic password hashes.
        """
        user_dict: Dict[str, Any] = {
            "id": self._id,
            "username": self._username,
            "email": self._email,
            "created_at": self._created_at.isoformat(),
        }
        if include_tasks:
            user_dict["tasks"] = [task.to_dict() for task in self.get_tasks()]
        return user_dict

    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User id={self._id!r} username={self._username!r}>"

    # -------------------------------------------------------------------------
    # In-Memory Repository Persistence Operations
    # -------------------------------------------------------------------------

    @classmethod
    def register(
        cls,
        username: str,
        password: str,
        email: str,
    ) -> "User":
        """
        Validate credentials, hash password, and persist a new user.

        Raises:
            ValidationError: If username, password, or email fails validation.
            UserAlreadyExistsError: If username or email is already registered.
        """
        clean_user: str = validate_username(username)
        clean_email: str = validate_email_format(email)
        validate_password_strength(password)

        if clean_user.lower() in cls._users_by_username:
            raise UserAlreadyExistsError(f"Username '{clean_user}' is already registered.")

        if clean_email.lower() in cls._users_by_email:
            raise UserAlreadyExistsError(f"Email '{clean_email}' is already registered.")

        hashed: str = hash_password(password)
        user: User = cls(username=clean_user, email=clean_email, password_hash=hashed)
        return user

    @classmethod
    def authenticate(
        cls,
        username: str,
        password: str,
    ) -> Optional["User"]:
        """
        Authenticate user credentials by username and password.

        Returns:
            User instance if credentials are valid, None otherwise.
        """
        if not username or not password:
            return None

        clean_user: str = str(username).strip().lower()
        user: Optional[User] = cls._users_by_username.get(clean_user)
        if user and user.check_password(password):
            return user
        return None

    @classmethod
    def get_by_id(cls, user_id: Union[str, int]) -> Optional["User"]:
        """Retrieve user by ID."""
        key: str = str(user_id)
        return cls._users_by_id.get(key)

    @classmethod
    def get_by_username(cls, username: str) -> Optional["User"]:
        """Retrieve user by username."""
        key: str = str(username).strip().lower()
        return cls._users_by_username.get(key)

    @classmethod
    def get_by_email(cls, email: str) -> Optional["User"]:
        """Retrieve user by email."""
        key: str = str(email).strip().lower()
        return cls._users_by_email.get(key)

    @classmethod
    def get_all(cls) -> List["User"]:
        """Retrieve all registered users."""
        return list(cls._users_by_id.values())

    @classmethod
    def delete_by_id(cls, user_id: Union[str, int]) -> bool:
        """Delete user by ID and purge secondary indexes."""
        key: str = str(user_id)
        user: Optional[User] = cls._users_by_id.pop(key, None)
        if user:
            cls._users_by_username.pop(user.username.lower(), None)
            cls._users_by_email.pop(user.email.lower(), None)
            # Cascade: delete user's tasks
            for task in list(Task.get_all()):
                if task.user_id == key:
                    Task.delete_by_id(task.id)
            return True
        return False

    @classmethod
    def clear_all(cls) -> None:
        """Clear all registered users and reset counter."""
        cls._users_by_id.clear()
        cls._users_by_username.clear()
        cls._users_by_email.clear()
        cls._id_counter = 0
