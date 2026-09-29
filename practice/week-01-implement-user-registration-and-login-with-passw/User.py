"""
User.py - User data model with secure registration, login, and password hashing.

Implements:
1. User registration with validation and duplicate prevention.
2. User login with password hash validation.
3. Secure password hashing using bcrypt or hashlib with cryptographic salt.
4. Timing-attack resistant password verification.
5. In-memory array-based task storage.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
from typing import Any, Callable, Dict, List, Optional, Union

# Optional bcrypt support
try:
    import bcrypt  # type: ignore
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

# Optional werkzeug support
try:
    from werkzeug.security import check_password_hash, generate_password_hash
    HAS_WERKZEUG = True
except ImportError:
    HAS_WERKZEUG = False


class _DualMethod:
    """
    Descriptor enabling a method to behave intuitively both when called
    on the class (e.g. User.login(username, password)) and on an instance
    (e.g. user.login(password) or user.login(username, password)).
    """

    def __init__(self, class_fn: Callable, instance_fn: Callable) -> None:
        self.class_fn = class_fn
        self.instance_fn = instance_fn
        self.__doc__ = class_fn.__doc__

    def __get__(self, instance: Optional[Any], owner: Optional[type] = None) -> Callable:
        if instance is None:
            return lambda *args, **kwargs: self.class_fn(owner, *args, **kwargs)
        return lambda *args, **kwargs: self.instance_fn(instance, *args, **kwargs)


class User:
    """
    User model representing an application user in the task manager system.

    Attributes:
        username (str): Unique username for identification.
        email (str): Contact email for the user.
        password_hash (str): Securely hashed password (never plaintext).
        tasks (List[Any]): Array storing the user's tasks.
        id (Optional[int]): Unique identifier for the user.
    """

    # In-memory user registries
    _users_by_username: Dict[str, User] = {}
    _users_by_email: Dict[str, User] = {}
    _users_list: List[User] = []
    _next_id: int = 1

    def __init__(
        self,
        username: str,
        email: str,
        password: Optional[str] = None,
        user_id: Optional[int] = None,
        hashing_method: Optional[str] = None,
    ) -> None:
        """
        Initialize a new User instance.

        Args:
            username: Non-empty string representing the username.
            email: Valid email string containing '@'.
            password: Optional plain text password to hash immediately.
            user_id: Optional numeric identifier for the user.
            hashing_method: Optional hashing algorithm ('bcrypt' or 'hashlib').

        Raises:
            TypeError: If username, email, or password is not a string.
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
        if not clean_email or "@" not in clean_email or not self._is_valid_email(clean_email):
            raise ValueError("Email must be a valid non-empty email address")
        self.email: str = clean_email

        self.id: Optional[int] = user_id
        self.password_hash: str = ""

        # Array-based task storage
        self.tasks: List[Any] = []

        if password is not None:
            if not isinstance(password, str):
                raise TypeError(f"Password must be a string, got {type(password).__name__}")
            if not password:
                raise ValueError("Password cannot be empty")
            self.set_password(password, method=hashing_method)

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Basic email format validation."""
        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        return bool(re.match(pattern, email))

    # ----------------------------------------------------------------------
    # Password Hashing & Verification
    # ----------------------------------------------------------------------

    @staticmethod
    def hash_password(password: str, method: Optional[str] = None) -> str:
        """
        Hash a plaintext password securely using bcrypt or hashlib with salt.

        Success criterion: Passwords hashed before storage.

        Args:
            password: Raw plaintext password to hash.
            method: Hashing method to use ('bcrypt', 'hashlib', or None for auto).

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

        selected_method = (method or "").lower()

        # Bcrypt hashing if requested or preferred when available
        if selected_method == "bcrypt" or (not selected_method and HAS_BCRYPT):
            if HAS_BCRYPT:
                salt = bcrypt.gensalt()
                hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), salt)
                return hashed_bytes.decode("utf-8")
            # If bcrypt specifically requested but not installed, fallback to hashlib
            pass

        # Hashlib secure hashing with random 16-byte salt and SHA-256
        salt_hex = os.urandom(16).hex()
        digest = hashlib.sha256(f"{salt_hex}${password}".encode("utf-8")).hexdigest()
        return f"sha256${salt_hex}${digest}"

    def set_password(self, password: str, method: Optional[str] = None) -> None:
        """
        Hash and store the user's password. The raw password is never stored.

        Args:
            password: Plain text password to hash and store.
            method: Optional hashing method ('bcrypt' or 'hashlib').

        Raises:
            TypeError: If password is not a string.
            ValueError: If password is empty.
        """
        if not isinstance(password, str):
            raise TypeError(f"Password must be a string, got {type(password).__name__}")
        if not password:
            raise ValueError("Password cannot be empty")
        self.password_hash = self.hash_password(password, method=method)

    def check_password(self, password: str) -> bool:
        """
        Verify a provided plaintext password against the stored password hash.
        Uses constant-time comparison to prevent timing attacks.

        Success criterion: Login validates hashed password.

        Args:
            password: Plain text password to verify.

        Returns:
            True if the password matches, False otherwise.
        """
        if not self.password_hash or not password:
            return False

        if not isinstance(password, str):
            return False

        # 1. Bcrypt hash verification
        if self.password_hash.startswith(("$2a$", "$2b$", "$2y$")):
            if HAS_BCRYPT:
                try:
                    return bcrypt.checkpw(
                        password.encode("utf-8"),
                        self.password_hash.encode("utf-8"),
                    )
                except Exception:
                    return False
            return False

        # 2. Hashlib salted SHA-256: sha256$salt$digest
        if self.password_hash.startswith("sha256$"):
            parts = self.password_hash.split("$", 2)
            if len(parts) == 3:
                salt_hex, stored_digest = parts[1], parts[2]
                computed_digest = hashlib.sha256(f"{salt_hex}${password}".encode("utf-8")).hexdigest()
                return hmac.compare_digest(stored_digest, computed_digest)

        # 3. Hashlib PBKDF2 format: pbkdf2:sha256:rounds$salt$digest
        if self.password_hash.startswith("pbkdf2:sha256:"):
            try:
                header, salt, stored_key = self.password_hash.split("$", 2)
                rounds = int(header.split(":")[-1])
                computed_key = hashlib.pbkdf2_hmac(
                    "sha256",
                    password.encode("utf-8"),
                    salt.encode("utf-8"),
                    rounds,
                ).hex()
                return hmac.compare_digest(stored_key, computed_key)
            except Exception:
                pass

        # 4. Werkzeug standard hash formats
        if HAS_WERKZEUG and (
            self.password_hash.startswith("scrypt:")
            or self.password_hash.startswith("pbkdf2:")
            or self.password_hash.startswith("argon2:")
        ):
            try:
                return check_password_hash(self.password_hash, password)
            except Exception:
                pass

        # 5. Raw SHA-256 fallback comparison
        computed = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(self.password_hash, computed)

    # ----------------------------------------------------------------------
    # User Registration and Login Functions
    # ----------------------------------------------------------------------

    @classmethod
    def _class_register(
        cls,
        username: str,
        email: str,
        password: str,
        user_id: Optional[int] = None,
        hashing_method: Optional[str] = None,
    ) -> User:
        """
        Register a new user with secure password hashing and persistence into registry.

        Args:
            username: Unique username string.
            email: Unique valid email string.
            password: Plaintext password (hashed before storage).
            user_id: Optional explicit user ID.
            hashing_method: Optional hashing method ('bcrypt' or 'hashlib').

        Returns:
            The registered User instance.

        Raises:
            TypeError: If input types are invalid.
            ValueError: If inputs are invalid or username/email already taken.
        """
        if not isinstance(username, str):
            raise TypeError(f"Username must be a string, got {type(username).__name__}")
        clean_username = username.strip()
        if not clean_username:
            raise ValueError("Username cannot be empty")

        if not isinstance(email, str):
            raise TypeError(f"Email must be a string, got {type(email).__name__}")
        clean_email = email.strip()
        if not clean_email or "@" not in clean_email or not cls._is_valid_email(clean_email):
            raise ValueError("Email must be a valid non-empty email address")

        if not isinstance(password, str):
            raise TypeError(f"Password must be a string, got {type(password).__name__}")
        if not password:
            raise ValueError("Password cannot be empty")

        # Duplicate checks (case-insensitive)
        if clean_username.lower() in cls._users_by_username:
            raise ValueError(f"Username '{clean_username}' is already taken.")
        if clean_email.lower() in cls._users_by_email:
            raise ValueError(f"Email '{clean_email}' is already registered.")

        assigned_id = user_id if user_id is not None else cls._next_id
        cls._next_id = max(cls._next_id, assigned_id + 1)

        user = cls(
            username=clean_username,
            email=clean_email,
            password=None,
            user_id=assigned_id,
        )
        # Success criterion: Passwords hashed before storage
        user.set_password(password, method=hashing_method)

        # Store in registry
        cls._users_by_username[clean_username.lower()] = user
        cls._users_by_email[clean_email.lower()] = user
        cls._users_list.append(user)

        return user

    def _instance_register(self, hashing_method: Optional[str] = None) -> User:
        """Register the current user instance into the class registry."""
        cls = self.__class__
        clean_username = self.username.strip()
        clean_email = self.email.strip()

        if clean_username.lower() in cls._users_by_username:
            existing = cls._users_by_username[clean_username.lower()]
            if existing is not self:
                raise ValueError(f"Username '{clean_username}' is already taken.")
        if clean_email.lower() in cls._users_by_email:
            existing = cls._users_by_email[clean_email.lower()]
            if existing is not self:
                raise ValueError(f"Email '{clean_email}' is already registered.")

        if self.id is None:
            self.id = cls._next_id
            cls._next_id += 1

        cls._users_by_username[clean_username.lower()] = self
        cls._users_by_email[clean_email.lower()] = self
        if self not in cls._users_list:
            cls._users_list.append(self)

        return self

    # Dual method for register: User.register(...) and user.register()
    register = _DualMethod(_class_register, _instance_register)

    @classmethod
    def _class_login(
        cls,
        username: str,
        password: str,
    ) -> Optional[User]:
        """
        Authenticate a user by username or email and validate their hashed password.

        Success criterion: Login validates hashed password.

        Args:
            username: Username or email of the user.
            password: Plaintext password to verify.

        Returns:
            The User instance if authentication succeeds, None otherwise.

        Raises:
            TypeError: If username or password is not a string.
            ValueError: If username is empty.
        """
        if not isinstance(username, str):
            raise TypeError(f"Username must be a string, got {type(username).__name__}")
        clean_username = username.strip()
        if not clean_username:
            raise ValueError("Username cannot be empty")

        if not isinstance(password, str):
            raise TypeError(f"Password must be a string, got {type(password).__name__}")
        if not password:
            return None

        # Look up by username or email
        user = cls.get_by_username(clean_username) or cls.get_by_email(clean_username)
        if not user:
            return None

        # Validate hashed password
        if user.check_password(password):
            return user
        return None

    def _instance_login(self, *args: Any, **kwargs: Any) -> Union[bool, Optional[User]]:
        """
        Instance login:
        - user.login("password") -> validates password and returns bool
        - user.login("username", "password") -> delegates to User.login classmethod
        """
        if len(args) == 1 and not kwargs and isinstance(args[0], str):
            return self.check_password(args[0])
        return self.__class__._class_login(*args, **kwargs)

    # Dual method for login: User.login(username, password) and user.login(password)
    login = _DualMethod(_class_login, _instance_login)

    # ----------------------------------------------------------------------
    # Registry Lookups & Helpers
    # ----------------------------------------------------------------------

    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered users from the in-memory registry."""
        cls._users_by_username.clear()
        cls._users_by_email.clear()
        cls._users_list.clear()
        cls._next_id = 1

    @classmethod
    def get_by_username(cls, username: str) -> Optional[User]:
        """Look up a user by username (case-insensitive)."""
        if not isinstance(username, str):
            return None
        return cls._users_by_username.get(username.strip().lower())

    @classmethod
    def get_by_email(cls, email: str) -> Optional[User]:
        """Look up a user by email (case-insensitive)."""
        if not isinstance(email, str):
            return None
        return cls._users_by_email.get(email.strip().lower())

    @classmethod
    def get_by_id(cls, user_id: int) -> Optional[User]:
        """Look up a user by user_id."""
        for u in cls._users_list:
            if u.id == user_id:
                return u
        return None

    @classmethod
    def get_all_users(cls) -> List[User]:
        """Return a copy of all registered users."""
        return list(cls._users_list)

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
        Excludes sensitive information like raw passwords or hashes.

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

    def __bool__(self) -> bool:
        """
        Ensure User instances always evaluate to True in boolean contexts,
        even when the tasks array is empty.
        """
        return True

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
        return f"<User id={self.id}, username='{self.username}', email='{self.email}', tasks_count={len(self.tasks)}>"


# Module-level convenience functions matching guidance:
# "1. Add register() and login() functions to User class"
register = User.register
login = User.login
