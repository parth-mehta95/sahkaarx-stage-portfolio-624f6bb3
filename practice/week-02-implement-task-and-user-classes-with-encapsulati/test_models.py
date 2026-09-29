"""
Unit tests for Task and User models with encapsulation and Flask routes.
Verifies private attributes (_name, _id), task creation, retrieval, update,
and Flask integration.
"""

import os
import sys
import unittest
import importlib.util

# Ensure local module directory is prioritized
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Explicitly load local week-02 models.py to prevent IDE analyzers from resolving to root models.py
_models_path = os.path.join(CURRENT_DIR, "models.py")
_models_spec = importlib.util.spec_from_file_location("week02_models", _models_path)
_models_module = importlib.util.module_from_spec(_models_spec)
sys.modules["models"] = _models_module
_models_spec.loader.exec_module(_models_module)

Task = _models_module.Task
User = _models_module.User

# Explicitly load local week-02 app.py
_app_path = os.path.join(CURRENT_DIR, "app.py")
_app_spec = importlib.util.spec_from_file_location("week02_app", _app_path)
_app_module = importlib.util.module_from_spec(_app_spec)
sys.modules["app"] = _app_module
_app_spec.loader.exec_module(_app_module)

app = _app_module.app


class TestTaskAndUserEncapsulation(unittest.TestCase):
    def setUp(self):
        User.clear_all()
        Task.clear_all()
        self.client = app.test_client()

    def test_task_private_attributes_and_encapsulation(self):
        """Verify Task uses private attributes (_id, _name, etc.)."""
        task = Task(id="t1", name="Write Code", description="Implement encapsulation")

        # Verify private attributes exist on instance
        self.assertTrue(hasattr(task, "_id"))
        self.assertTrue(hasattr(task, "_name"))
        self.assertTrue(hasattr(task, "_description"))
        self.assertEqual(task._id, "t1")
        self.assertEqual(task._name, "Write Code")

        # Verify property getters work
        self.assertEqual(task.id, "t1")
        self.assertEqual(task.name, "Write Code")
        self.assertEqual(task.title, "Write Code")
        self.assertEqual(task.description, "Implement encapsulation")
        self.assertEqual(task.status, "pending")
        self.assertFalse(task.completed)

        # Verify property setters
        task.name = "Refactor Code"
        self.assertEqual(task._name, "Refactor Code")
        self.assertEqual(task.name, "Refactor Code")

        task.completed = True
        self.assertTrue(task._completed)
        self.assertEqual(task._status, "completed")

    def test_user_private_attributes_and_encapsulation(self):
        """Verify User uses private attributes (_id, _name, etc.)."""
        user = User(id="u1", name="Alice", email="alice@example.com")

        self.assertTrue(hasattr(user, "_id"))
        self.assertTrue(hasattr(user, "_name"))
        self.assertTrue(hasattr(user, "_email"))
        self.assertEqual(user._id, "u1")
        self.assertEqual(user._name, "Alice")

        # Verify properties
        self.assertEqual(user.id, "u1")
        self.assertEqual(user.name, "Alice")
        self.assertEqual(user.email, "alice@example.com")

        user.name = "Alice Updated"
        self.assertEqual(user._name, "Alice Updated")
        self.assertEqual(user.name, "Alice Updated")

    def test_task_creation_retrieval_and_update(self):
        """Verify Task creation, retrieval, and update methods."""
        # Creation
        task = Task.create(id="t100", name="Initial Task", description="Initial Desc")
        self.assertIsNotNone(task)
        self.assertEqual(task.name, "Initial Task")

        # Retrieval
        retrieved = Task.get_by_id("t100")
        self.assertEqual(retrieved, task)
        self.assertEqual(len(Task.get_all()), 1)

        # Update
        updated = Task.update_by_id("t100", name="Updated Task Title", status="in_progress")
        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, "Updated Task Title")
        self.assertEqual(updated.status, "in_progress")

    def test_user_task_methods(self):
        """Verify task methods on User class."""
        user = User.create(id="u1", name="Bob", email="bob@example.com")

        # User task creation
        task = user.create_task(id="t1", name="User Task 1", description="Details")
        self.assertIsNotNone(task)
        self.assertEqual(task.user_id, "u1")
        self.assertEqual(len(user.tasks), 1)

        # User task retrieval
        retrieved_task = user.get_task("t1")
        self.assertEqual(retrieved_task, task)
        self.assertEqual(len(user.get_all_tasks()), 1)

        # User task update
        updated_task = user.update_task("t1", name="User Task 1 Updated", completed=True)
        self.assertEqual(updated_task.name, "User Task 1 Updated")
        self.assertTrue(updated_task.completed)

        # User task deletion
        success = user.delete_task("t1")
        self.assertTrue(success)
        self.assertIsNone(user.get_task("t1"))
        self.assertEqual(len(user.get_all_tasks()), 0)

    def test_flask_routes_using_class_methods(self):
        """Verify Flask routes operate using class methods without direct dict operations."""
        # 1. Create User
        user_res = self.client.post("/users", json={"name": "Charlie", "email": "charlie@example.com"})
        self.assertEqual(user_res.status_code, 201)
        user_data = user_res.get_json()["user"]
        user_id = user_data["id"]

        # 2. Retrieve User
        get_user_res = self.client.get(f"/users/{user_id}")
        self.assertEqual(get_user_res.status_code, 200)

        # 3. Create Task via user route
        task_res = self.client.post(f"/users/{user_id}/tasks", json={
            "name": "Design OOP architecture",
            "description": "Use private attributes and properties"
        })
        self.assertEqual(task_res.status_code, 201)
        task_data = task_res.get_json()["task"]
        task_id = task_data["id"]

        # 4. Retrieve User Tasks
        list_tasks_res = self.client.get(f"/users/{user_id}/tasks")
        self.assertEqual(list_tasks_res.status_code, 200)
        self.assertEqual(len(list_tasks_res.get_json()["tasks"]), 1)

        # 5. Retrieve Specific Task
        get_task_res = self.client.get(f"/users/{user_id}/tasks/{task_id}")
        self.assertEqual(get_task_res.status_code, 200)
        self.assertEqual(get_task_res.get_json()["task"]["name"], "Design OOP architecture")

        # 6. Update Task
        update_task_res = self.client.put(f"/users/{user_id}/tasks/{task_id}", json={
            "name": "Design OOP architecture (Completed)",
            "completed": True
        })
        self.assertEqual(update_task_res.status_code, 200)
        self.assertTrue(update_task_res.get_json()["task"]["completed"])

        # 7. Delete Task
        delete_task_res = self.client.delete(f"/users/{user_id}/tasks/{task_id}")
        self.assertEqual(delete_task_res.status_code, 200)

        # 8. Verify Deleted
        verify_res = self.client.get(f"/users/{user_id}/tasks/{task_id}")
        self.assertEqual(verify_res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
