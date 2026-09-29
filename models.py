"""models.py - SQLAlchemy models with complete Python type hints."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db: SQLAlchemy = SQLAlchemy()


class User(db.Model):  # type: ignore[name-defined]
    """User model representing application users."""

    __tablename__: str = "users"

    id: int = db.Column(db.Integer, primary_key=True)
    username: str = db.Column(db.String(80), unique=True, nullable=False)
    email: str = db.Column(db.String(120), unique=True, nullable=False)
    password_hash: str = db.Column(db.String(256), nullable=False)

    tasks = db.relationship(
        "Task",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __init__(
        self,
        username: str,
        email: str,
        password: Optional[str] = None,
    ) -> None:
        """Initialize a new User instance with validation."""
        if not isinstance(username, str):
            raise TypeError(f"Username must be a string, got {type(username).__name__}")
        clean_username = username.strip()
        if not clean_username:
            raise ValueError("Username cannot be empty")
        self.username: str = clean_username

        if not isinstance(email, str):
            raise TypeError(f"Email must be a string, got {type(email).__name__}")
        clean_email = email.strip()
        if not clean_email or "@" not in clean_email:
            raise ValueError("Email must be a valid non-empty email address")
        self.email: str = clean_email

        if password is not None:
            if not isinstance(password, str):
                raise TypeError(f"Password must be a string, got {type(password).__name__}")
            if not password:
                raise ValueError("Password cannot be empty")
            self.set_password(password)

    def set_password(self, password: str) -> None:
        """Hash and store the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the user's password against the stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @classmethod
    def register(cls, username: str, email: str, password: str) -> User:
        """Register and persist a new user with hashed password."""
        user: User = cls(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional[User]:
        """Authenticate user credentials and return user instance if valid."""
        user: Optional[User] = cls.query.filter_by(username=username).first()
        if user and user.check_password(password):
            return user
        return None

    @classmethod
    def login(cls, username: str, password: str) -> Optional[User]:
        """Authenticate user credentials and return user instance if valid."""
        return cls.authenticate(username=username, password=password)

    def get_tasks(self) -> List[Task]:
        """Retrieve all tasks associated with this user."""
        return list(self.tasks)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize user model to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
        }

    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User {self.username}>"


# Re-attach type annotations for __init__ in case SQLAlchemy declarative alters them
User.__init__.__annotations__ = {
    "username": str,
    "email": str,
    "password": Optional[str],
    "return": None,
}


class Task(db.Model):  # type: ignore[name-defined]
    """Task model representing tasks created by users."""

    __tablename__: str = "tasks"

    id: int = db.Column(db.Integer, primary_key=True)
    title: str = db.Column(db.String(200), nullable=False)
    description: Optional[str] = db.Column(db.Text, nullable=True, default="")
    due_date: Optional[date] = db.Column(db.Date, nullable=True)
    status: str = db.Column(db.String(50), nullable=False, default="pending")
    completed: bool = db.Column(db.Boolean, nullable=False, default=False)
    user_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
    )

    def __init__(
        self,
        title: str,
        description: Optional[str] = "",
        due_date: Optional[Union[date, datetime, str]] = None,
        status: str = "pending",
        completed: bool = False,
        user_id: Optional[int] = None,
    ) -> None:
        """Initialize a new Task instance with validation."""
        if not isinstance(title, str):
            raise TypeError(f"Title must be a string, got {type(title).__name__}")
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Title cannot be empty")
        self.title: str = clean_title

        if description is not None and not isinstance(description, str):
            raise TypeError(f"Description must be a string, got {type(description).__name__}")
        self.description: Optional[str] = description.strip() if description else ""

        self.due_date: Optional[date] = self._parse_date(due_date)

        if not isinstance(status, str):
            raise TypeError(f"Status must be a string, got {type(status).__name__}")
        clean_status = status.strip()
        if not clean_status:
            raise ValueError("Status cannot be empty")
        self.status: str = clean_status

        if not isinstance(completed, bool):
            raise TypeError(f"Completed must be a boolean, got {type(completed).__name__}")
        self.completed: bool = completed

        if user_id is not None:
            if not isinstance(user_id, int) or isinstance(user_id, bool):
                raise TypeError(f"User ID must be an integer, got {type(user_id).__name__}")
            if user_id <= 0:
                raise ValueError("User ID must be a positive integer")
        self.user_id: Optional[int] = user_id

    @staticmethod
    def _parse_date(
        due_date: Optional[Union[date, datetime, str]],
    ) -> Optional[date]:
        """Helper to parse date from string, datetime, or date."""
        if due_date is None:
            return None
        if isinstance(due_date, datetime):
            return due_date.date()
        if isinstance(due_date, date):
            return due_date
        if isinstance(due_date, str):
            return datetime.strptime(due_date.strip(), "%Y-%m-%d").date()
        raise ValueError(f"Unsupported date format: {due_date}")

    def update(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        due_date: Optional[Union[date, datetime, str]] = None,
        status: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> None:
        """Update task attributes with type-annotated parameters."""
        if title is not None:
            if not isinstance(title, str):
                raise TypeError(f"Title must be a string, got {type(title).__name__}")
            clean_title = title.strip()
            if not clean_title:
                raise ValueError("Title cannot be empty")
            self.title = clean_title

        if description is not None:
            if not isinstance(description, str):
                raise TypeError(f"Description must be a string, got {type(description).__name__}")
            self.description = description.strip()

        if due_date is not None:
            self.due_date = self._parse_date(due_date)

        if status is not None:
            if not isinstance(status, str):
                raise TypeError(f"Status must be a string, got {type(status).__name__}")
            clean_status = status.strip()
            if not clean_status:
                raise ValueError("Status cannot be empty")
            self.status = clean_status
            if clean_status.lower() == "completed":
                self.completed = True

        if completed is not None:
            if not isinstance(completed, bool):
                raise TypeError(f"Completed must be a boolean, got {type(completed).__name__}")
            self.completed = completed
            if completed:
                self.status = "completed"

    def mark_completed(self) -> None:
        """Mark task as completed."""
        self.completed = True
        self.status = "completed"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize task model to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "completed": self.completed,
            "user_id": self.user_id,
        }

    def __repr__(self) -> str:
        """String representation of Task."""
        return f"<Task {self.id}: {self.title}>"


# Re-attach type annotations for __init__ in case SQLAlchemy declarative alters them
Task.__init__.__annotations__ = {
    "title": str,
    "description": Optional[str],
    "due_date": Optional[Union[date, datetime, str]],
    "status": str,
    "completed": bool,
    "user_id": Optional[int],
    "return": None,
}
