"""
test_routes.py - Comprehensive Unit & Integration Tests for Refactored REST Endpoints.

Tests all CRUD operations, SQLAlchemy ORM queries, database persistence,
and HTTP status codes (200, 201, 404, 400).
"""
import json
import os
import tempfile
import unittest

from models import Task, User, db
from routes import create_app


class TestRoutesDatabasePersistence(unittest.TestCase):
    """Test suite for verifying REST endpoints, ORM queries, and DB persistence."""

    def setUp(self):
        """Set up an isolated temporary SQLite database for each test run."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.app = create_app(f"sqlite:///{self.db_path}")
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        """Clean up and remove the temporary SQLite database file."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        try:
            os.close(self.db_fd)
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except OSError:
            pass

    # ========================================================================
    # 1. POST /tasks Tests (201 Created, 400 Bad Request, DB Persistence)
    # ========================================================================

    def test_post_task_success_201_persists_to_database(self):
        """POST /tasks should return 201 and persist the task to SQLite via ORM."""
        payload = {
            "title": "Build ORM Query Refactoring",
            "description": "Refactor in-memory task lists to SQLAlchemy",
            "due_date": "2026-10-15",
            "status": "pending",
        }
        response = self.client.post(
            "/tasks",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn("task", data)
        task_id = data["task"]["id"]
        self.assertEqual(data["task"]["title"], "Build ORM Query Refactoring")
        self.assertEqual(data["task"]["description"], "Refactor in-memory task lists to SQLAlchemy")

        # Verify DB Persistence using a direct ORM query
        with self.app.app_context():
            persisted_task = Task.query.get(task_id)
            self.assertIsNotNone(persisted_task)
            self.assertEqual(persisted_task.title, "Build ORM Query Refactoring")
            self.assertEqual(persisted_task.status, "pending")
            self.assertFalse(persisted_task.completed)

    def test_post_task_missing_title_returns_400(self):
        """POST /tasks without title should return 400 Bad Request."""
        payload = {"description": "No title provided"}
        response = self.client.post(
            "/tasks",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error"], "Bad Request")

        # Verify no task was persisted
        with self.app.app_context():
            self.assertEqual(Task.query.count(), 0)

    def test_post_task_empty_title_returns_400(self):
        """POST /tasks with whitespace/empty title should return 400 Bad Request."""
        payload = {"title": "   ", "description": "Empty title"}
        response = self.client.post(
            "/tasks",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_post_task_with_user_relationship_201(self):
        """POST /tasks with user_id creates relational link and returns 201."""
        # First register a user
        with self.app.app_context():
            user = User(username="alice", email="alice@example.com")
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        payload = {
            "title": "Assigned Task",
            "description": "Task for Alice",
            "user_id": user_id,
        }
        response = self.client.post(
            "/tasks",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        task_id = data["task"]["id"]

        # Verify DB foreign key persistence and user.tasks relationship
        with self.app.app_context():
            user_in_db = User.query.get(user_id)
            self.assertEqual(len(user_in_db.tasks), 1)
            self.assertEqual(user_in_db.tasks[0].id, task_id)

    def test_post_task_with_nonexistent_user_id_returns_400(self):
        """POST /tasks with invalid user_id foreign key returns 400 Bad Request."""
        payload = {
            "title": "Orphaned Task",
            "user_id": 99999,
        }
        response = self.client.post(
            "/tasks",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # ========================================================================
    # 2. GET /tasks Tests (200 OK, ORM Query Filtering)
    # ========================================================================

    def test_get_all_tasks_returns_200(self):
        """GET /tasks retrieves all persisted tasks via ORM and returns 200."""
        with self.app.app_context():
            t1 = Task(title="Task 1", status="pending")
            t2 = Task(title="Task 2", status="completed", completed=True)
            db.session.add_all([t1, t2])
            db.session.commit()

        response = self.client.get("/tasks")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["tasks"]), 2)
        titles = [t["title"] for t in data["tasks"]]
        self.assertIn("Task 1", titles)
        self.assertIn("Task 2", titles)

    def test_get_tasks_filter_by_status(self):
        """GET /tasks?status=completed filters tasks via ORM query."""
        with self.app.app_context():
            t1 = Task(title="Task 1", status="pending")
            t2 = Task(title="Task 2", status="completed", completed=True)
            db.session.add_all([t1, t2])
            db.session.commit()

        response = self.client.get("/tasks?status=completed")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["tasks"][0]["title"], "Task 2")

    # ========================================================================
    # 3. GET /tasks/<id> Tests (200 OK, 404 Not Found, 400 Bad Request)
    # ========================================================================

    def test_get_single_task_success_200(self):
        """GET /tasks/<id> retrieves specific task by primary key."""
        with self.app.app_context():
            task = Task(title="Specific Task", description="Detailed notes")
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        response = self.client.get(f"/tasks/{task_id}")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["id"], task_id)
        self.assertEqual(data["title"], "Specific Task")

    def test_get_single_task_not_found_404(self):
        """GET /tasks/<id> for non-existent ID returns 404 Not Found."""
        response = self.client.get("/tasks/99999")
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data["error"], "Not Found")

    def test_get_single_task_invalid_id_400(self):
        """GET /tasks/<id> with non-numeric ID returns 400 Bad Request."""
        response = self.client.get("/tasks/not-a-number")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error"], "Bad Request")

    # ========================================================================
    # 4. PUT /tasks/<id> Tests (200 OK, 404 Not Found, 400 Bad Request, Persistence)
    # ========================================================================

    def test_put_task_success_200_persists_to_database(self):
        """PUT /tasks/<id> updates existing task and persists changes to DB."""
        with self.app.app_context():
            task = Task(title="Original Title", status="pending")
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        update_payload = {
            "title": "Updated Title",
            "description": "Added description",
            "status": "completed",
            "completed": True,
        }
        response = self.client.put(
            f"/tasks/{task_id}",
            data=json.dumps(update_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["task"]["title"], "Updated Title")
        self.assertEqual(data["task"]["status"], "completed")

        # Verify DB Persistence
        with self.app.app_context():
            updated_task = Task.query.get(task_id)
            self.assertEqual(updated_task.title, "Updated Title")
            self.assertEqual(updated_task.description, "Added description")
            self.assertEqual(updated_task.status, "completed")
            self.assertTrue(updated_task.completed)

    def test_put_task_not_found_returns_404(self):
        """PUT /tasks/<id> on non-existent task returns 404 Not Found."""
        response = self.client.put(
            "/tasks/99999",
            data=json.dumps({"title": "Doesn't Exist"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_put_task_empty_title_returns_400(self):
        """PUT /tasks/<id> with empty title returns 400 Bad Request."""
        with self.app.app_context():
            task = Task(title="Valid Title")
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        response = self.client.put(
            f"/tasks/{task_id}",
            data=json.dumps({"title": "  "}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # ========================================================================
    # 5. DELETE /tasks/<id> Tests (200 OK, 404 Not Found, 400 Bad Request, Persistence)
    # ========================================================================

    def test_delete_task_success_200_removes_from_database(self):
        """DELETE /tasks/<id> deletes record from SQLite and returns 200."""
        with self.app.app_context():
            task = Task(title="Task to be deleted")
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        response = self.client.delete(f"/tasks/{task_id}")
        self.assertEqual(response.status_code, 200)

        # Verify task is permanently deleted from database
        with self.app.app_context():
            deleted_task = Task.query.get(task_id)
            self.assertIsNone(deleted_task)

    def test_delete_task_not_found_returns_404(self):
        """DELETE /tasks/<id> for non-existent task returns 404 Not Found."""
        response = self.client.delete("/tasks/99999")
        self.assertEqual(response.status_code, 404)

    def test_delete_task_invalid_id_returns_400(self):
        """DELETE /tasks/<id> with invalid non-numeric ID returns 400."""
        response = self.client.delete("/tasks/invalid-id")
        self.assertEqual(response.status_code, 400)

    # ========================================================================
    # 6. User and Relationship ORM Query Tests
    # ========================================================================

    def test_user_and_relationship_queries(self):
        """Test user creation, retrieval, and relational task queries."""
        # 1. Create User -> 201 Created
        user_payload = {"username": "bob", "email": "bob@example.com"}
        user_res = self.client.post(
            "/users",
            data=json.dumps(user_payload),
            content_type="application/json",
        )
        self.assertEqual(user_res.status_code, 201)
        user_id = user_res.get_json()["user"]["id"]

        # 2. Duplicate User -> 400 Bad Request
        dup_res = self.client.post(
            "/users",
            data=json.dumps(user_payload),
            content_type="application/json",
        )
        self.assertEqual(dup_res.status_code, 400)

        # 3. Create Task via user endpoint -> 201 Created
        task_payload = {"title": "Bob's Work"}
        rel_task_res = self.client.post(
            f"/users/{user_id}/tasks",
            data=json.dumps(task_payload),
            content_type="application/json",
        )
        self.assertEqual(rel_task_res.status_code, 201)

        # 4. Query user tasks relationship endpoint -> 200 OK
        get_user_tasks_res = self.client.get(f"/users/{user_id}/tasks")
        self.assertEqual(get_user_tasks_res.status_code, 200)
        data = get_user_tasks_res.get_json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["tasks"][0]["title"], "Bob's Work")


if __name__ == "__main__":
    unittest.main()
