"""
test_routes.py - Automated Unit & Integration Tests for Task CRUD REST API.

Tests:
1. POST /tasks: Task creation returns HTTP 201 Created and valid JSON.
2. POST /tasks: Missing title or non-JSON returns HTTP 400 Bad Request.
3. GET /tasks: Retrieve all tasks returns HTTP 200 OK and valid JSON array.
4. GET /tasks/<id>: Retrieve single task returns HTTP 200 OK and valid JSON.
5. GET /tasks/<id>: Non-existent task returns HTTP 404 Not Found.
6. PUT /tasks/<id>: Update task returns HTTP 200 OK and updated JSON.
7. PUT /tasks/<id>: Non-existent task returns HTTP 404 Not Found.
8. PUT /tasks/<id>: Empty title update returns HTTP 400 Bad Request.
9. DELETE /tasks/<id>: Delete task returns HTTP 200 OK.
10. DELETE /tasks/<id>: Delete non-existent task returns HTTP 404 Not Found.
11. Content-Type and JSON validity verification across all endpoints.
"""

from __future__ import annotations

import json
import unittest
from routes import app, reset_db, add_task


class TestTaskCRUDEndpoints(unittest.TestCase):
    """Test suite verifying CRUD operations and status code compliance."""

    def setUp(self) -> None:
        """Reset in-memory storage and configure Flask test client before each test."""
        reset_db()
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        """Clean up database after each test."""
        reset_db()

    # -------------------------------------------------------------------------
    # 1. POST /tasks (Task Creation - 201 Created)
    # -------------------------------------------------------------------------

    def test_create_task_success_status_201(self) -> None:
        """Verify POST /tasks creates a new task and returns HTTP 201 Created."""
        payload = {
            "title": "Complete Week 03 REST API",
            "description": "Implement CRUD endpoints and status codes",
            "status": "in_progress",
        }
        response = self.client.post(
            "/tasks",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.content_type, "application/json")

        data = response.get_json()
        self.assertIsNotNone(data)
        self.assertIn("task", data)
        task = data["task"]
        self.assertEqual(task["id"], 1)
        self.assertEqual(task["title"], "Complete Week 03 REST API")
        self.assertEqual(task["description"], "Implement CRUD endpoints and status codes")
        self.assertEqual(task["status"], "in_progress")
        self.assertIn("created_at", task)
        self.assertIn("updated_at", task)

    def test_create_task_missing_title_status_400(self) -> None:
        """Verify POST /tasks with missing title returns HTTP 400 Bad Request."""
        payload = {
            "description": "Task without title",
        }
        response = self.client.post(
            "/tasks",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Bad Request")

    def test_create_task_empty_title_status_400(self) -> None:
        """Verify POST /tasks with empty whitespace title returns HTTP 400 Bad Request."""
        payload = {
            "title": "   ",
        }
        response = self.client.post(
            "/tasks",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_create_task_non_json_payload_status_400(self) -> None:
        """Verify POST /tasks with non-JSON body returns HTTP 400 Bad Request."""
        response = self.client.post(
            "/tasks",
            data="not-a-json-string",
            content_type="text/plain",
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    # -------------------------------------------------------------------------
    # 2. GET /tasks (Retrieve All Tasks - 200 OK)
    # -------------------------------------------------------------------------

    def test_get_all_tasks_empty_status_200(self) -> None:
        """Verify GET /tasks returns empty list with HTTP 200 OK when no tasks exist."""
        response = self.client.get("/tasks")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        data = response.get_json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["tasks"], [])

    def test_get_all_tasks_populated_status_200(self) -> None:
        """Verify GET /tasks returns all stored tasks with HTTP 200 OK."""
        add_task(title="Task One", description="First task")
        add_task(title="Task Two", description="Second task", status="completed")

        response = self.client.get("/tasks")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["tasks"]), 2)
        self.assertEqual(data["tasks"][0]["title"], "Task One")
        self.assertEqual(data["tasks"][1]["title"], "Task Two")

    def test_get_all_tasks_filter_by_status(self) -> None:
        """Verify GET /tasks?status=completed filters tasks accurately."""
        add_task(title="Task One", status="pending")
        add_task(title="Task Two", status="completed")

        response = self.client.get("/tasks?status=completed")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["tasks"][0]["title"], "Task Two")

    # -------------------------------------------------------------------------
    # 3. GET /tasks/<id> (Retrieve Single Task - 200 OK / 404 Not Found)
    # -------------------------------------------------------------------------

    def test_get_task_by_id_found_status_200(self) -> None:
        """Verify GET /tasks/<id> returns single task with HTTP 200 OK."""
        created = add_task(title="Inspectable Task", description="Details")
        task_id = created["id"]

        response = self.client.get(f"/tasks/{task_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        data = response.get_json()
        self.assertEqual(data["id"], task_id)
        self.assertEqual(data["title"], "Inspectable Task")

    def test_get_task_by_id_not_found_status_404(self) -> None:
        """Verify GET /tasks/<id> with non-existent id returns HTTP 404 Not Found."""
        response = self.client.get("/tasks/9999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content_type, "application/json")
        data = response.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn("9999", data["message"])

    # -------------------------------------------------------------------------
    # 4. PUT /tasks/<id> (Update Task - 200 OK / 400 Bad Request / 404 Not Found)
    # -------------------------------------------------------------------------

    def test_update_task_success_status_200(self) -> None:
        """Verify PUT /tasks/<id> updates existing task and returns HTTP 200 OK."""
        created = add_task(title="Original Title", status="pending")
        task_id = created["id"]

        payload = {
            "title": "Updated Title",
            "status": "completed",
            "description": "Updated Description",
        }
        response = self.client.put(
            f"/tasks/{task_id}",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        data = response.get_json()
        self.assertIn("task", data)
        self.assertEqual(data["task"]["title"], "Updated Title")
        self.assertEqual(data["task"]["status"], "completed")
        self.assertEqual(data["task"]["description"], "Updated Description")

    def test_update_task_not_found_status_404(self) -> None:
        """Verify PUT /tasks/<id> for non-existent id returns HTTP 404 Not Found."""
        payload = {"title": "Will Not Update"}
        response = self.client.put(
            "/tasks/9999",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data["error"], "Not Found")

    def test_update_task_empty_title_status_400(self) -> None:
        """Verify PUT /tasks/<id> with empty title returns HTTP 400 Bad Request."""
        created = add_task(title="Original")
        task_id = created["id"]

        payload = {"title": "  "}
        response = self.client.put(
            f"/tasks/{task_id}",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error"], "Bad Request")

    # -------------------------------------------------------------------------
    # 5. DELETE /tasks/<id> (Delete Task - 200 OK / 404 Not Found)
    # -------------------------------------------------------------------------

    def test_delete_task_success_status_200(self) -> None:
        """Verify DELETE /tasks/<id> deletes existing task and returns HTTP 200 OK."""
        created = add_task(title="To Be Deleted")
        task_id = created["id"]

        response = self.client.delete(f"/tasks/{task_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        data = response.get_json()
        self.assertIn("deleted successfully", data["message"])

        # Confirm task is now gone (404)
        followup = self.client.get(f"/tasks/{task_id}")
        self.assertEqual(followup.status_code, 404)

    def test_delete_task_not_found_status_404(self) -> None:
        """Verify DELETE /tasks/<id> for non-existent id returns HTTP 404 Not Found."""
        response = self.client.delete("/tasks/9999")

        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data["error"], "Not Found")

    # -------------------------------------------------------------------------
    # 6. Global Route & Error Handling (Root & 405 Method Not Allowed)
    # -------------------------------------------------------------------------

    def test_root_route_status_200(self) -> None:
        """Verify GET / returns API index and status 200."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("endpoints", data)

    def test_method_not_allowed_status_405(self) -> None:
        """Verify unsupported HTTP method returns HTTP 405 Method Not Allowed."""
        response = self.client.delete("/tasks")  # DELETE not allowed on collection
        self.assertEqual(response.status_code, 405)
        data = response.get_json()
        self.assertEqual(data["error"], "Method Not Allowed")


if __name__ == "__main__":
    unittest.main()
