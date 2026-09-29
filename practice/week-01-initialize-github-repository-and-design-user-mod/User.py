"""
User.py - User data model for Task Manager backend.

Implements the User class with:
- Array-based task storage (stores tasks in an array/list)
- Basic password hashing and verification
- Input validation, task management, and serialization methods
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any, Dict, List, Optional, Union

try:
    from werkzeug.security import check_password_hash, generate_password_hash
    HAS_WERKZEUG = True
except ImportError:
    HAS_WERKZEUG = False


class User:
    """
    User model representing an application user in the task manager system.

    Attributes:
        username (str): Unique username for identification.
        email (str): Contact email for the user.
        password_hash (str): Securely hashed password.
        tasks (List[Any]): Array storing the user's tasks.
        id (Optional[int]): Optional unique identifier for database integration.
    """

    def __init__(
        self,
        username: str,
        email: str,
        password: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> None:
        """
        Initialize a new User instance.

        Args:
            username: Non-empty string representing the username.
            email: Valid email string containing '@'.
            password: Optional plain text password to hash immediately.
            user_id: Optional numeric identifier for the user.

        Raises:
            TypeError: If username or email is not a string.
            ValueError: If username or email is empty or invalid format.
        """
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

        self.id: Optional[int] = user_id
        self.password_hash: str = ""

        # Success criteria: User class stores tasks in array (Python list)
        self.tasks: List[Any] = []

        if password is not None:
            if not isinstance(password, str):
                raise TypeError(f"Password must be a string, got {type(password).__name__}")
            if not password:
                raise ValueError("Password cannot be empty")
            self.set_password(password)

    # ----------------------------------------------------------------------
    # Password Hashing & Verification
    # ----------------------------------------------------------------------

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a plaintext password using werkzeug if available or hashlib sha256 with salt.

        Args:
            password: Raw plaintext password to hash.

        Returns:
            Hashed password string.

        Raises:
            TypeError: If password is not a string.
            ValueError: If password is empty.
        """
        if not isinstance(password, str):
            raise TypeError(f"Password must be a string, got {type(password).__name__}")
        if not password:
            raise ValueError("Password cannot be empty")

        if HAS_WERKZEUG:
            return generate_password_hash(password)

        # Standard library fallback using hashlib SHA-256 with random salt
        salt = os.urandom(16).hex()
        digest = hashlib.sha256(f"{salt}${password}".encode("utf-8")).hexdigest()
        return f"sha256${salt}${digest}"

    def set_password(self, password: str) -> None:
        """
        Hash and store the user's password.

        Args:
            password: Plain text password to hash.

        Raises:
            TypeError: If password is not a string.
            ValueError: If password is empty.
        """
        if not isinstance(password, str):
            raise TypeError(f"Password must be a string, got {type(password).__name__}")
        if not password:
            raise ValueError("Password cannot be empty")
        self.password_hash = self.hash_password(password)

    def check_password(self, password: str) -> bool:
        """
        Verify a provided plaintext password against the stored password hash.

        Args:
            password: Plain text password to verify.

        Returns:
            True if the password matches, False otherwise.
        """
        if not self.password_hash or not password:
            return False

        if not isinstance(password, str):
            return False

        # If hashed using Werkzeug standard schemes
        if HAS_WERKZEUG and (
            self.password_hash.startswith("scrypt:")
            or self.password_hash.startswith("pbkdf2:")
            or self.password_hash.startswith("argon2:")
        ):
            return check_password_hash(self.password_hash, password)

        # Check if hash was created using salted sha256: sha256$salt$digest
        if self.password_hash.startswith("sha256$"):
            parts = self.password_hash.split("$", 2)
            if len(parts) == 3:
                salt, stored_digest = parts[1], parts[2]
                computed_digest = hashlib.sha256(f"{salt}${password}".encode("utf-8")).hexdigest()
                return hmac.compare_digest(stored_digest, computed_digest)

        # Werkzeug fallback
        if HAS_WERKZEUG:
            try:
                return check_password_hash(self.password_hash, password)
            except Exception:
                pass

        # Raw SHA-256 fallback comparison
        computed = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(self.password_hash, computed)

    # ----------------------------------------------------------------------
    # Task Array Storage & Management
    # ----------------------------------------------------------------------

    def add_task(self, task: Any) -> Any:
        """
        Add a task to the user's task array.

        Args:
            task: Task object, dictionary, or string representation.

        Returns:
            The added task.

        Raises:
            ValueError: If task is None.
        """
        if task is None:
            raise ValueError("Task cannot be None")
        self.tasks.append(task)
        return task

    def get_tasks(self) -> List[Any]:
        """
        Retrieve the array of tasks belonging to this user.

        Returns:
            A list containing all tasks.
        """
        return self.tasks

    def remove_task(self, task: Any) -> bool:
        """
        Remove a task from the user's task array.

        Args:
            task: Task object, dict, or identifier to remove.

        Returns:
            True if task was removed, False if not found.
        """
        if task in self.tasks:
            self.tasks.remove(task)
            return True

        # Check by id if task is an object or dict
        for idx, item in enumerate(self.tasks):
            if isinstance(item, dict) and item.get("id") == task:
                self.tasks.pop(idx)
                return True
            if hasattr(item, "id") and getattr(item, "id") == task:
                self.tasks.pop(idx)
                return True
        return False

    def clear_tasks(self) -> None:
        """Clear all tasks from the user's task array."""
        self.tasks.clear()

    def get_task_by_id(self, task_id: Any) -> Optional[Any]:
        """
        Find and return a task by its identifier.

        Args:
            task_id: Unique task identifier.

        Returns:
            The matching task or None if not found.
        """
        for item in self.tasks:
            if isinstance(item, dict) and item.get("id") == task_id:
                return item
            if hasattr(item, "id") and getattr(item, "id") == task_id:
                return item
        return None

    # ----------------------------------------------------------------------
    # Serialization & Dunder Methods
    # ----------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the User instance to a dictionary representation.
        Excludes sensitive information like raw passwords.

        Returns:
            Dictionary with user metadata and serialized tasks.
        """
        serialized_tasks = []
        for t in self.tasks:
            if hasattr(t, "to_dict") and callable(t.to_dict):
                serialized_tasks.append(t.to_dict())
            elif isinstance(t, dict):
                serialized_tasks.append(t)
            else:
                serialized_tasks.append(str(t))

        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "tasks": serialized_tasks,
            "task_count": len(self.tasks),
        }

    def __len__(self) -> int:
        """Return the number of tasks stored in the user's task array."""
        return len(self.tasks)

    def __getitem__(self, index: int) -> Any:
        """Allow indexing access directly into the task array."""
        return self.tasks[index]

    def __iter__(self):
        """Allow iteration over the user's tasks."""
        return iter(self.tasks)

    def __repr__(self) -> str:
        """String representation of User instance."""
        return f"<User username='{self.username}', email='{self.email}', tasks_count={len(self.tasks)}>"
