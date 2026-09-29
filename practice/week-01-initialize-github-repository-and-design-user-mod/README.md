# Initialize GitHub Repository and Design User Model

## Task Brief
Set up GitHub repo, design User and Task data models, implement User class with array-based task storage and basic password hashing.

## Scenario
Your team needs a task manager backend. Initialize the repo and scaffold core data models.

## Deliverables
- GitHub repo with User class

## Success Criteria
- User class stores tasks in array

---

# Task Manager Backend - Architecture & Design Specification

## 1. Overview
The Task Manager backend is an object-oriented Python application designed to manage users, authentication, and user-assigned tasks. In this initial phase, the foundation is established by implementing the core data models:
- **`User`**: Handles identity, password hashing, and in-memory array-based task containment.
- **`Task`**: Encapsulates task details including title, description, due date, and completion status.

## 2. Architecture & Design Principles

### 2.1 Array-Based Task Storage
- Each `User` instance maintains an internal array (`self.tasks = []`) representing all tasks owned by that user.
- This adheres directly to the primary success criterion: **User class stores tasks in array**.
- The `User` class provides convenient collection manipulation methods:
  - `add_task(task)`: Appends a new task to the array.
  - `get_tasks()`: Retrieves the array of tasks.
  - `remove_task(task)`: Removes a task by object identity or identifier.
  - `get_task_by_id(task_id)`: Lookups in the array by ID.
  - `clear_tasks()`: Empties the user's task array.
  - Standard dunder support: `__len__`, `__getitem__`, and `__iter__` for intuitive list-like interaction (`len(user)`, `user[0]`, `for t in user:`).

### 2.2 Password Security & Hashing
- User passwords are **never** stored in plain text.
- Passwords passed during instantiation (`User(..., password="...")`) or via `set_password(password)` are securely hashed.
- The implementation supports `werkzeug.security` (`generate_password_hash` and `check_password_hash`) when running in environments with Werkzeug installed.
- For zero-dependency standalone execution, it provides an automatic cryptographic fallback using `hashlib.sha256` combined with a unique random 16-byte salt (`os.urandom(16)`) and `hmac.compare_digest` to prevent timing attacks.
- Verification is performed safely via `check_password(candidate_password)`.

### 2.3 Data Validation & Type Safety
- **Type Checking**: Both `User` and `Task` enforce runtime type and format checks.
- **Validation**:
  - `username` must be a non-empty string.
  - `email` must be a non-empty string containing a valid `@` symbol.
  - `password` cannot be empty.
  - `Task.title` must be a non-empty string.
  - `Task.due_date` flexibly parses `date`, `datetime`, or formatted date strings (`YYYY-MM-DD`).

## 3. Project Structure

```text
practice/week-01-initialize-github-repository-and-design-user-mod/
├── README.md       # Architecture specification and task brief
├── User.py         # User class with task array storage & password hashing
├── Task.py         # Task class representing task entities
└── test_user.py    # Unit tests validating models, task storage, and security
```

## 4. Class API Reference

### `User` Class (`User.py`)
| Member | Type | Description |
|---|---|---|
| `username` | `str` | User's unique display/login name |
| `email` | `str` | User's registered email address |
| `password_hash` | `str` | Hashed representation of user password |
| `tasks` | `List[Any]` | In-memory array storing user tasks (**Success Criterion**) |
| `id` | `Optional[int]` | Optional user identifier |
| `set_password(password)` | Method | Hashes and stores password |
| `check_password(password)` | Method | Returns boolean indicating match |
| `add_task(task)` | Method | Appends task to the user's tasks array |
| `get_tasks()` | Method | Returns user's tasks list |
| `remove_task(task)` | Method | Removes task from array by reference or id |
| `clear_tasks()` | Method | Clears all tasks from user array |
| `get_task_by_id(task_id)` | Method | Finds task in array by its ID |
| `to_dict()` | Method | Returns sanitized dictionary serialization |

### `Task` Class (`Task.py`)
| Member | Type | Description |
|---|---|---|
| `title` | `str` | Task title / summary |
| `description` | `Optional[str]` | Optional details about the task |
| `status` | `str` | Status string (`pending`, `completed`, etc.) |
| `completed` | `bool` | Completion boolean indicator |
| `due_date` | `Optional[date]` | Due date for the task |
| `mark_completed()` | Method | Sets status to completed and completed flag to True |
| `to_dict()` | Method | Returns dictionary serialization |

## 5. Usage Example

```python
from User import User
from Task import Task

# 1. Initialize user with hashed password
user = User(
    username="developer1",
    email="dev@example.com",
    password="super_secret_password"
)

# 2. Verify password authentication
assert user.check_password("super_secret_password") is True
assert user.check_password("wrong_password") is False
assert user.password_hash != "super_secret_password"

# 3. Add tasks to user's task array (Success Criteria)
task1 = Task(title="Scaffold repository", description="Create initial file structure")
task2 = Task(title="Implement models", description="Add User and Task classes")

user.add_task(task1)
user.add_task(task2)

# 4. Access and manage tasks
print(f"User {user.username} has {len(user)} tasks:")
for task in user.get_tasks():
    print(f"- {task.title} [{task.status}]")

# Mark first task completed
user[0].mark_completed()
print("Task 1 completed:", user[0].completed)

# 5. Serialization
user_dict = user.to_dict()
print(user_dict)
```

## 6. Running Tests
Run the provided test suite using `pytest`:
```bash
pytest test_user.py -v
```