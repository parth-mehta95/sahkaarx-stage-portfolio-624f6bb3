"""
Models module for Task Manager application.
Defines Task and User classes using encapsulation with private attributes (_name, _id, etc.).
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid


class Task:
    """
    Task model representing a single task in the task manager.
    Encapsulates task attributes using private variables (_id, _name, etc.).
    """
    _registry: Dict[str, "Task"] = {}

    def __init__(
        self,
        id: Optional[str] = None,
        name: str = "",
        title: Optional[str] = None,
        description: str = "",
        status: str = "pending",
        completed: bool = False,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ):
        # Resolve ID from id, task_id, kwargs, or auto-generate
        resolved_id = id if id is not None else task_id
        if resolved_id is None:
            resolved_id = kwargs.get("id") or kwargs.get("task_id")
        self._id: str = str(resolved_id) if resolved_id is not None else str(uuid.uuid4())

        # Resolve Name from name, title, kwargs
        resolved_name = title if title is not None else name
        if not resolved_name:
            resolved_name = kwargs.get("name") or kwargs.get("title") or ""
        self._name: str = str(resolved_name)

        self._description: str = str(description or kwargs.get("description", ""))
        self._status: str = str(status or kwargs.get("status", "pending"))
        self._completed: bool = bool(completed if completed is not False else kwargs.get("completed", False))

        resolved_user_id = user_id if user_id is not None else kwargs.get("user_id")
        self._user_id: Optional[str] = str(resolved_user_id) if resolved_user_id is not None else None

        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

        # Register instance in class-level registry
        Task._registry[self._id] = self

    # --- Property Getters and Setters (Encapsulation) ---

    @property
    def id(self) -> str:
        """Get private task ID."""
        return self._id

    @property
    def name(self) -> str:
        """Get private task name."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """Set private task name."""
        if not value or not str(value).strip():
            raise ValueError("Task name cannot be empty.")
        self._name = str(value).strip()
        self._updated_at = datetime.now()

    @property
    def title(self) -> str:
        """Alias for task name."""
        return self._name

    @title.setter
    def title(self, value: str) -> None:
        """Set task name via title alias."""
        self.name = value

    @property
    def description(self) -> str:
        """Get private task description."""
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        """Set private task description."""
        self._description = str(value)
        self._updated_at = datetime.now()

    @property
    def status(self) -> str:
        """Get private task status."""
        return self._status

    @status.setter
    def status(self, value: str) -> None:
        """Set private task status."""
        self._status = str(value)
        if self._status.lower() in ("completed", "done"):
            self._completed = True
        elif self._status.lower() in ("pending", "in_progress", "todo"):
            self._completed = False
        self._updated_at = datetime.now()

    @property
    def completed(self) -> bool:
        """Get private completion status."""
        return self._completed

    @completed.setter
    def completed(self, value: bool) -> None:
        """Set private completion status."""
        self._completed = bool(value)
        self._status = "completed" if self._completed else "pending"
        self._updated_at = datetime.now()

    @property
    def user_id(self) -> Optional[str]:
        """Get associated user ID."""
        return self._user_id

    @user_id.setter
    def user_id(self, value: Optional[str]) -> None:
        """Set associated user ID."""
        self._user_id = str(value) if value is not None else None
        self._updated_at = datetime.now()

    @property
    def created_at(self) -> datetime:
        """Get task creation timestamp."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """Get task last update timestamp."""
        return self._updated_at

    # --- Instance Methods ---

    def update(
        self,
        name: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        completed: Optional[bool] = None,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> "Task":
        """Update task fields with encapsulation."""
        if title is not None:
            self.name = title
        elif name is not None:
            self.name = name
        elif "name" in kwargs:
            self.name = kwargs["name"]
        elif "title" in kwargs:
            self.name = kwargs["title"]

        if description is not None:
            self.description = description
        elif "description" in kwargs:
            self.description = kwargs["description"]

        if status is not None:
            self.status = status
        elif "status" in kwargs:
            self.status = kwargs["status"]

        if completed is not None:
            self.completed = completed
        elif "completed" in kwargs:
            self.completed = kwargs["completed"]

        if user_id is not None:
            self.user_id = user_id
        elif "user_id" in kwargs:
            self.user_id = kwargs["user_id"]

        self._updated_at = datetime.now()
        return self

    def mark_completed(self) -> "Task":
        """Mark task as completed."""
        self.completed = True
        return self

    def mark_pending(self) -> "Task":
        """Mark task as pending."""
        self.completed = False
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert task object to dictionary representation."""
        return {
            "id": self._id,
            "name": self._name,
            "title": self._name,
            "description": self._description,
            "status": self._status,
            "completed": self._completed,
            "user_id": self._user_id,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    # --- Class Methods for Task Creation, Retrieval, and Update ---

    @classmethod
    def create(
        cls,
        id: Optional[str] = None,
        name: str = "",
        title: Optional[str] = None,
        description: str = "",
        status: str = "pending",
        completed: bool = False,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> "Task":
        """Class method to create and register a new Task."""
        resolved_id = id if id is not None else task_id
        task = cls(
            id=resolved_id,
            name=name,
            title=title,
            description=description,
            status=status,
            completed=completed,
            user_id=user_id,
            *args,
            **kwargs,
        )
        return task

    @classmethod
    def get_by_id(cls, task_id: str) -> Optional["Task"]:
        """Class method to retrieve a Task by its ID."""
        return cls._registry.get(str(task_id))

    @classmethod
    def get_all(cls) -> List["Task"]:
        """Class method to retrieve all tasks."""
        return list(cls._registry.values())

    @classmethod
    def filter_by_user(cls, user_id: str) -> List["Task"]:
        """Class method to retrieve all tasks belonging to a user."""
        return [task for task in cls._registry.values() if task.user_id == str(user_id)]

    @classmethod
    def update_by_id(cls, task_id: str, **kwargs: Any) -> Optional["Task"]:
        """Class method to update a Task by its ID."""
        task = cls.get_by_id(task_id)
        if task is None:
            return None
        return task.update(**kwargs)

    @classmethod
    def delete_by_id(cls, task_id: str) -> bool:
        """Class method to delete a Task by its ID."""
        task_id_str = str(task_id)
        if task_id_str in cls._registry:
            del cls._registry[task_id_str]
            return True
        return False

    @classmethod
    def clear_all(cls) -> None:
        """Clear task registry (useful for testing)."""
        cls._registry.clear()


class User:
    """
    User model representing a user in the task manager.
    Encapsulates user attributes (_id, _name, etc.) and provides task methods.
    """
    _registry: Dict[str, "User"] = {}

    def __init__(
        self,
        id: Optional[str] = None,
        name: str = "",
        username: Optional[str] = None,
        email: str = "",
        password: str = "",
        user_id: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ):
        # Resolve ID from id, user_id, kwargs, or auto-generate
        resolved_id = id if id is not None else user_id
        if resolved_id is None:
            resolved_id = kwargs.get("id") or kwargs.get("user_id")
        self._id: str = str(resolved_id) if resolved_id is not None else str(uuid.uuid4())

        # Resolve Name from name, username, kwargs
        resolved_name = username if username is not None else name
        if not resolved_name:
            resolved_name = kwargs.get("name") or kwargs.get("username") or ""
        self._name: str = str(resolved_name)

        self._email: str = str(email or kwargs.get("email", ""))
        self._password: str = str(password or kwargs.get("password", ""))
        self._tasks: Dict[str, Task] = {}
        self._created_at: datetime = datetime.now()

        # Register instance in class-level registry
        User._registry[self._id] = self

    # --- Property Getters and Setters (Encapsulation) ---

    @property
    def id(self) -> str:
        """Get private user ID."""
        return self._id

    @property
    def name(self) -> str:
        """Get private user name."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """Set private user name."""
        if not value or not str(value).strip():
            raise ValueError("User name cannot be empty.")
        self._name = str(value).strip()

    @property
    def username(self) -> str:
        """Alias for user name."""
        return self._name

    @username.setter
    def username(self, value: str) -> None:
        """Set user name via username alias."""
        self.name = value

    @property
    def email(self) -> str:
        """Get private user email."""
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        """Set private user email."""
        self._email = str(value).strip()

    @property
    def password(self) -> str:
        """Get private user password."""
        return self._password

    @password.setter
    def password(self, value: str) -> None:
        """Set private user password."""
        self._password = str(value)

    @property
    def tasks(self) -> List[Task]:
        """Get user's tasks list."""
        return list(self._tasks.values())

    # --- Task Creation, Retrieval, and Update Methods on User Class ---

    def create_task(
        self,
        id: Optional[str] = None,
        name: str = "",
        title: Optional[str] = None,
        description: str = "",
        status: str = "pending",
        completed: bool = False,
        task_id: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Task:
        """
        Create a new Task encapsulated under this User.
        """
        resolved_id = id if id is not None else task_id
        task = Task.create(
            id=resolved_id,
            name=name,
            title=title,
            description=description,
            status=status,
            completed=completed,
            user_id=self._id,
            *args,
            **kwargs,
        )
        self._tasks[task.id] = task
        return task

    def add_task(self, task: Task) -> Task:
        """Add an existing task to this user."""
        task.user_id = self._id
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task belonging to this user by task ID."""
        return self._tasks.get(str(task_id))

    def get_all_tasks(self) -> List[Task]:
        """Retrieve all tasks belonging to this user."""
        return list(self._tasks.values())

    def update_task(self, task_id: str, **kwargs: Any) -> Optional[Task]:
        """Update a task belonging to this user."""
        task = self.get_task(task_id)
        if task is None:
            return None
        return task.update(**kwargs)

    def delete_task(self, task_id: str) -> bool:
        """Remove a task belonging to this user."""
        task_id_str = str(task_id)
        if task_id_str in self._tasks:
            del self._tasks[task_id_str]
            Task.delete_by_id(task_id_str)
            return True
        return False

    def to_dict(self, include_tasks: bool = False) -> Dict[str, Any]:
        """Convert user object to dictionary representation."""
        data: Dict[str, Any] = {
            "id": self._id,
            "name": self._name,
            "username": self._name,
            "email": self._email,
            "task_count": len(self._tasks),
            "created_at": self._created_at.isoformat(),
        }
        if include_tasks:
            data["tasks"] = [t.to_dict() for t in self._tasks.values()]
        return data

    # --- Class Methods for User & User-Task Management ---

    @classmethod
    def create(
        cls,
        id: Optional[str] = None,
        name: str = "",
        username: Optional[str] = None,
        email: str = "",
        password: str = "",
        user_id: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> "User":
        """Class method to create and register a new User."""
        resolved_id = id if id is not None else user_id
        user = cls(
            id=resolved_id,
            name=name,
            username=username,
            email=email,
            password=password,
            *args,
            **kwargs,
        )
        return user

    @classmethod
    def get_by_id(cls, user_id: str) -> Optional["User"]:
        """Class method to retrieve a User by ID."""
        return cls._registry.get(str(user_id))

    @classmethod
    def get_all(cls) -> List["User"]:
        """Class method to retrieve all users."""
        return list(cls._registry.values())

    @classmethod
    def create_user_task(cls, user_id: str, **task_kwargs: Any) -> Optional[Task]:
        """Class method to create a task for a given user."""
        user = cls.get_by_id(user_id)
        if user is None:
            return None
        return user.create_task(**task_kwargs)

    @classmethod
    def get_user_task(cls, user_id: str, task_id: str) -> Optional[Task]:
        """Class method to retrieve a specific task of a user."""
        user = cls.get_by_id(user_id)
        if user is None:
            return None
        return user.get_task(task_id)

    @classmethod
    def get_user_tasks(cls, user_id: str) -> Optional[List[Task]]:
        """Class method to retrieve all tasks of a user."""
        user = cls.get_by_id(user_id)
        if user is None:
            return None
        return user.get_all_tasks()

    @classmethod
    def update_user_task(cls, user_id: str, task_id: str, **kwargs: Any) -> Optional[Task]:
        """Class method to update a task for a given user."""
        user = cls.get_by_id(user_id)
        if user is None:
            return None
        return user.update_task(task_id, **kwargs)

    @classmethod
    def delete_user_task(cls, user_id: str, task_id: str) -> bool:
        """Class method to delete a task for a given user."""
        user = cls.get_by_id(user_id)
        if user is None:
            return False
        return user.delete_task(task_id)

    @classmethod
    def clear_all(cls) -> None:
        """Clear user registry and class registries."""
        cls._registry.clear()
        Task.clear_all()
