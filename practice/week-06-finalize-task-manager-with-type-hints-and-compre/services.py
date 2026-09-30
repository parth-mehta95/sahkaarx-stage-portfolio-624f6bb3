"""
services.py - Type-Hinted Business Service Layer for Task Manager Application.

Deliverables & Architecture:
- Service layer orchestrating domain models (User, Task) and business transactions.
- Clean separation between HTTP routing controllers and core business rules.
- Fully type-annotated method signatures.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure current directory is in sys.path
current_dir: str = str(Path(__file__).resolve().parent)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from models import NotFoundError, Task, User, ValidationError
except ImportError:  # pragma: no cover
    from .models import NotFoundError, Task, User, ValidationError


class UserService:
    """Service handling user account registration, authentication, and retrieval."""

    @staticmethod
    def register_user(username: str, email: str, password: str) -> User:
        """
        Register a new user account with validated credentials.

        Args:
            username: Alphanumeric username.
            email: Valid email address.
            password: Secure password string.

        Returns:
            The newly created User instance.
        """
        return User.register(username=username, email=email, password=password)

    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        """
        Authenticate user credentials.

        Args:
            username: Registered username.
            password: Plaintext password.

        Returns:
            The authenticated User if valid, None otherwise.
        """
        return User.authenticate(username=username, password=password)

    @staticmethod
    def get_user_by_id(user_id: Union[str, int]) -> Optional[User]:
        """Retrieve user by identifier."""
        return User.get_by_id(user_id)

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Retrieve user by username."""
        return User.get_by_username(username)

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Retrieve user by email address."""
        return User.get_by_email(email)

    @staticmethod
    def list_users() -> List[User]:
        """Retrieve a list of all registered users."""
        return User.get_all()

    @staticmethod
    def delete_user(user_id: Union[str, int]) -> bool:
        """Delete user by ID."""
        return User.delete_by_id(user_id)


class TaskService:
    """Service handling task creation, status updates, filtering, and deletion."""

    @staticmethod
    def create_task(
        title: str,
        description: str = "",
        status: str = "pending",
        user_id: Optional[Union[str, int]] = None,
    ) -> Task:
        """
        Create a new task instance.

        Args:
            title: Task title.
            description: Optional task details.
            status: Task status string ('pending', 'in_progress', 'completed', 'archived').
            user_id: Optional owner user ID.

        Returns:
            The created Task entity.
        """
        if user_id is not None:
            user: Optional[User] = User.get_by_id(user_id)
            if user:
                return user.create_task(
                    title=title,
                    description=description,
                    status=status,
                )

        return Task.create(
            title=title,
            description=description,
            status=status,
            user_id=user_id,
        )

    @staticmethod
    def get_task_by_id(task_id: Union[str, int]) -> Optional[Task]:
        """Retrieve a task entity by ID."""
        return Task.get_by_id(task_id)

    @staticmethod
    def list_tasks(
        user_id: Optional[Union[str, int]] = None,
        status: Optional[str] = None,
    ) -> List[Task]:
        """
        Query tasks filtered by user_id and/or status.

        Args:
            user_id: Filter by owner user ID.
            status: Filter by status string.

        Returns:
            List of matching Task entities.
        """
        return Task.filter_by(user_id=user_id, status=status)

    @staticmethod
    def update_task(task_id: Union[str, int], **kwargs: Any) -> Optional[Task]:
        """
        Update fields on an existing task.

        Args:
            task_id: Task identifier.
            **kwargs: Fields to update.

        Returns:
            Updated Task entity, or None if task was not found.
        """
        task: Optional[Task] = Task.get_by_id(task_id)
        if task is None:
            return None
        task.update(**kwargs)
        return task

    @staticmethod
    def mark_task_completed(task_id: Union[str, int]) -> Optional[Task]:
        """Mark an existing task as completed."""
        task: Optional[Task] = Task.get_by_id(task_id)
        if task is None:
            return None
        task.mark_completed()
        return task

    @staticmethod
    def delete_task(task_id: Union[str, int]) -> bool:
        """
        Delete a task by ID.

        Returns:
            True if task existed and was deleted, False otherwise.
        """
        return Task.delete_by_id(task_id)
