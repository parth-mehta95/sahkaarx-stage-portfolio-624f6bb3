"""
Task.py - Task data model for Task Manager.

Implements the Task class representing individual tasks that can be
stored in a User's task array.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional, Union


class Task:
    """
    Task model representing an individual task in the task manager.

    Attributes:
        id (Optional[int]): Unique task identifier.
        title (str): Title or summary of the task.
        description (Optional[str]): Detailed description of the task.
        status (str): Current status ('pending', 'in-progress', 'completed').
        completed (bool): Completion flag.
        due_date (Optional[date]): Due date for the task.
        user_id (Optional[int]): Foreign key or user identifier.
    """

    def __init__(
        self,
        title: str,
        description: Optional[str] = None,
        status: str = "pending",
        completed: bool = False,
        due_date: Optional[Union[date, datetime, str]] = None,
        user_id: Optional[int] = None,
        task_id: Optional[int] = None,
    ) -> None:
        """
        Initialize a new Task instance.

        Args:
            title: Non-empty string representing task title.
            description: Optional detailed description.
            status: Status string (defaults to 'pending').
            completed: Boolean flag indicating completion.
            due_date: Optional date, datetime, or date-string (YYYY-MM-DD).
            user_id: Optional user identifier.
            task_id: Optional task identifier.

        Raises:
            TypeError: If title or description types are invalid.
            ValueError: If title is empty.
        """
        if not isinstance(title, str):
            raise TypeError(f"Title must be a string, got {type(title).__name__}")
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Task title cannot be empty")
        self.title: str = clean_title

        if description is not None and not isinstance(description, str):
            raise TypeError(f"Description must be a string, got {type(description).__name__}")
        self.description: Optional[str] = description.strip() if description else None

        self.status: str = status
        self.completed: bool = completed or (status.lower() == "completed")
        self.due_date: Optional[date] = self._parse_date(due_date) if due_date else None
        self.user_id: Optional[int] = user_id
        self.id: Optional[int] = task_id

    @staticmethod
    def _parse_date(val: Optional[Union[date, datetime, str]]) -> Optional[date]:
        """Parse various date formats into a datetime.date instance."""
        if val is None:
            return None
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        if isinstance(val, str):
            clean_str = val.strip()
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(clean_str, fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse date string: {val}")
        raise TypeError(f"Expected date, datetime, or str, got {type(val).__name__}")

    def mark_completed(self) -> None:
        """Mark task as completed and update status."""
        self.completed = True
        self.status = "completed"

    def mark_pending(self) -> None:
        """Mark task as pending."""
        self.completed = False
        self.status = "pending"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize Task instance to dictionary format."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "completed": self.completed,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "user_id": self.user_id,
        }

    def __repr__(self) -> str:
        """String representation of Task instance."""
        return f"<Task id={self.id}, title='{self.title}', status='{self.status}', completed={self.completed}>"
