"""models.py - SQLAlchemy ORM models and query functions for User and Task."""
from __future__ import annotations

from datetime import date, datetime
import sqlite3
from typing import Any, Dict, List, Optional, Union
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.security import check_password_hash, generate_password_hash

db: SQLAlchemy = SQLAlchemy()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    """Enforce SQLite foreign key referential integrity on each connection."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()


def create_app(database_uri: str = "sqlite:///:memory:") -> Flask:
    """Application factory for testing and production environments."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True
    db.init_app(app)
    return app


class User(db.Model):
    """User ORM model representing application users."""

    __tablename__: str = "users"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username: str = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email: str = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash: str = db.Column(db.String(256), nullable=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # 1-to-many relationship with Task
    tasks = db.relationship(
        "Task",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __init__(
        self,
        username: str,
        email: str,
        password: Optional[str] = None,
    ) -> None:
        """Initialize User model with validations."""
        if not isinstance(username, str):
            raise TypeError(f"Username must be a string, got {type(username).__name__}")
        clean_username = username.strip()
        if not clean_username:
            raise ValueError("Username cannot be empty")
        self.username = clean_username

        if not isinstance(email, str):
            raise TypeError(f"Email must be a string, got {type(email).__name__}")
        clean_email = email.strip()
        if not clean_email or "@" not in clean_email:
            raise ValueError("Email must be a valid non-empty email address")
        self.email = clean_email

        if password is not None:
            if not isinstance(password, str):
                raise TypeError(f"Password must be a string, got {type(password).__name__}")
            if not password:
                raise ValueError("Password cannot be empty")
            self.set_password(password)

    def set_password(self, password: str) -> None:
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password against hashed password."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize User instance to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "task_count": len(self.tasks) if self.tasks else 0,
        }

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Task(db.Model):
    """Task ORM model representing tasks assigned to users."""

    __tablename__: str = "tasks"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title: str = db.Column(db.String(200), nullable=False)
    description: Optional[str] = db.Column(db.Text, nullable=True, default="")
    due_date: Optional[date] = db.Column(db.Date, nullable=True)
    status: str = db.Column(db.String(50), nullable=False, default="pending")
    completed: bool = db.Column(db.Boolean, nullable=False, default=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Foreign key linking task to user
    user_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
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
        """Initialize Task model with validations."""
        if not isinstance(title, str):
            raise TypeError(f"Title must be a string, got {type(title).__name__}")
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Title cannot be empty")
        self.title = clean_title

        if description is not None and not isinstance(description, str):
            raise TypeError(f"Description must be a string, got {type(description).__name__}")
        self.description = description.strip() if description else ""

        self.due_date = self._parse_date(due_date)

        if not isinstance(status, str):
            raise TypeError(f"Status must be a string, got {type(status).__name__}")
        clean_status = status.strip().lower()
        if not clean_status:
            raise ValueError("Status cannot be empty")
        if clean_status not in {"pending", "in_progress", "completed", "cancelled"}:
            raise ValueError(f"Invalid status: {clean_status}")
        self.status = clean_status

        if not isinstance(completed, bool):
            raise TypeError(f"Completed must be a boolean, got {type(completed).__name__}")
        self.completed = completed or (self.status == "completed")

        if user_id is not None:
            if not isinstance(user_id, int) or isinstance(user_id, bool):
                raise TypeError(f"User ID must be an integer, got {type(user_id).__name__}")
            if user_id <= 0:
                raise ValueError("User ID must be a positive integer")
        self.user_id = user_id

    @staticmethod
    def _parse_date(due_date: Optional[Union[date, datetime, str]]) -> Optional[date]:
        """Parse various date formats into date object."""
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
        """Update task properties."""
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
            clean_status = status.strip().lower()
            if clean_status not in {"pending", "in_progress", "completed", "cancelled"}:
                raise ValueError(f"Invalid status: {clean_status}")
            self.status = clean_status
            if clean_status == "completed":
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
        """Serialize Task instance to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "completed": self.completed,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Task {self.id}: {self.title}>"


# ============================================================================
# Database Query Functions
# ============================================================================

def create_user(username: str, email: str, password: str) -> User:
    """Create and persist a new user."""
    user = User(username=username, email=email, password=password)
    db.session.add(user)
    db.session.commit()
    return user


def get_user_by_id(user_id: int) -> Optional[User]:
    """Retrieve user by primary key ID."""
    return db.session.get(User, user_id) if hasattr(db.session, "get") else User.query.get(user_id)


def get_user_by_username(username: str) -> Optional[User]:
    """Retrieve user by username."""
    return User.query.filter_by(username=username).first()


def get_user_by_email(email: str) -> Optional[User]:
    """Retrieve user by email address."""
    return User.query.filter_by(email=email).first()


def create_task(
    title: str,
    user_id: int,
    description: Optional[str] = "",
    due_date: Optional[Union[date, datetime, str]] = None,
    status: str = "pending",
    completed: bool = False,
) -> Task:
    """Create and persist a new task associated with a user."""
    task = Task(
        title=title,
        description=description,
        due_date=due_date,
        status=status,
        completed=completed,
        user_id=user_id,
    )
    db.session.add(task)
    db.session.commit()
    return task


def get_task_by_id(task_id: int) -> Optional[Task]:
    """Retrieve a task by primary key ID."""
    return db.session.get(Task, task_id) if hasattr(db.session, "get") else Task.query.get(task_id)


def get_tasks_for_user(
    user_id: int,
    status: Optional[str] = None,
    completed: Optional[bool] = None,
) -> List[Task]:
    """Retrieve all tasks belonging to a specific user with optional filters."""
    query = Task.query.filter_by(user_id=user_id)
    if status is not None:
        query = query.filter_by(status=status)
    if completed is not None:
        query = query.filter_by(completed=completed)
    return query.order_by(Task.created_at.desc()).all()


def get_completed_tasks_for_user(user_id: int) -> List[Task]:
    """Retrieve only completed tasks for a specific user."""
    return get_tasks_for_user(user_id=user_id, completed=True)


def get_pending_tasks_for_user(user_id: int) -> List[Task]:
    """Retrieve only pending tasks for a specific user."""
    return get_tasks_for_user(user_id=user_id, status="pending")


def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[Union[date, datetime, str]] = None,
    status: Optional[str] = None,
    completed: Optional[bool] = None,
) -> Optional[Task]:
    """Update an existing task and commit changes."""
    task = get_task_by_id(task_id)
    if not task:
        return None
    task.update(
        title=title,
        description=description,
        due_date=due_date,
        status=status,
        completed=completed,
    )
    db.session.commit()
    return task


def delete_task(task_id: int) -> bool:
    """Delete a task by ID."""
    task = get_task_by_id(task_id)
    if not task:
        return False
    db.session.delete(task)
    db.session.commit()
    return True
