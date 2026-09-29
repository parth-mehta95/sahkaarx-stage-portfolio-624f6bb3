# Build REST API Endpoints for Task CRUD

## Task Brief
Develop Flask endpoints for Create, Read, Update, Delete task operations with proper HTTP methods and status codes.

## Scenario
Your team needs REST endpoints for task operations. Build CRUD endpoints using proper HTTP methods and status codes.

## Deliverables
- Flask CRUD endpoints
- HTTP status code handling

## Success Criteria
- All CRUD operations return correct HTTP status codes
- Endpoints accept and return valid JSON

---

## 1. REST API Architecture & Overview

This Task Manager REST API is implemented in Flask, providing full CRUD (Create, Read, Update, Delete) capabilities for task entities. The implementation strictly adheres to REST principles:
- **Stateless Communication**: Every request contains all necessary data for execution.
- **Resource-Oriented URIs**: Nouns (`/tasks`, `/tasks/<id>`) represent resources rather than actions.
- **Standard HTTP Verbs**: `POST`, `GET`, `PUT`, `DELETE` map directly to CRUD operations.
- **Strict Status Code Semantics**: Accurate status codes convey outcome without ambiguity (`201`, `200`, `400`, `404`, `405`, `500`).
- **Standard JSON Payloads**: All incoming requests and outgoing responses use `application/json`.

### Project Artifacts
- **[`routes.py`](file:///d:/challengers%20testing/sahkaarx-stage-portfolio-624f6bb3/practice/week-03-build-rest-api-endpoints-for-task-crud/routes.py)**: Core REST endpoints Blueprint (`tasks_bp`), in-memory storage, and route handlers.
- **[`app.py`](file:///d:/challengers%20testing/sahkaarx-stage-portfolio-624f6bb3/practice/week-03-build-rest-api-endpoints-for-task-crud/app.py)**: Flask application factory and execution entry point.
- **[`test_routes.py`](file:///d:/challengers%20testing/sahkaarx-stage-portfolio-624f6bb3/practice/week-03-build-rest-api-endpoints-for-task-crud/test_routes.py)**: Automated unit and integration test suite covering all CRUD methods and status codes.

---

## 2. Endpoints Summary

| HTTP Method | Endpoint | Success Status | Error Statuses | Description |
|:---|:---|:---:|:---:|:---|
| `POST` | `/tasks` | `201 Created` | `400 Bad Request` | Creates a new task |
| `GET` | `/tasks` | `200 OK` | `500 Internal Error` | Retrieves all tasks (supports query filtering) |
| `GET` | `/tasks/<id>` | `200 OK` | `404 Not Found` | Retrieves a single task by ID |
| `PUT` | `/tasks/<id>` | `200 OK` | `400 Bad Request`, `404 Not Found` | Updates an existing task by ID |
| `DELETE` | `/tasks/<id>` | `200 OK` | `404 Not Found` | Deletes a task by ID |
| `GET` | `/` | `200 OK` | `500 Internal Error` | API discovery and service health check |

---

## 3. Detailed Endpoint Documentation

### 3.1 Create Task (`POST /tasks`)

Creates a new task record in the system.

- **URL**: `/tasks`
- **Method**: `POST`
- **Headers**:
  - `Content-Type: application/json`

#### Request Body Schema
| Field | Type | Required | Default | Description |
|:---|:---|:---:|:---|:---|
| `title` | `string` | **Yes** | — | Non-empty task title/summary |
| `description` | `string` | No | `""` | Additional task context/details |
| `status` | `string` | No | `"pending"` | Initial status (`pending`, `in_progress`, `completed`) |

#### Request Example
```json
{
  "title": "Configure Flask CRUD routes",
  "description": "Implement POST, GET, PUT, and DELETE with status codes",
  "status": "pending"
}
```

#### Successful Response (`201 Created`)
```json
{
  "message": "Task created successfully",
  "task": {
    "id": 1,
    "title": "Configure Flask CRUD routes",
    "description": "Implement POST, GET, PUT, and DELETE with status codes",
    "status": "pending",
    "created_at": "2026-09-29T12:00:00.000000+00:00",
    "updated_at": "2026-09-29T12:00:00.000000+00:00"
  }
}
```

#### Error Responses
- **`400 Bad Request`** (Missing or non-string title):
  ```json
  {
    "error": "Bad Request",
    "message": "Field 'title' is required and must be a non-empty string"
  }
  ```
- **`400 Bad Request`** (Missing or invalid JSON body):
  ```json
  {
    "error": "Bad Request",
    "message": "Request must contain valid application/json body"
  }
  ```

---

### 3.2 Retrieve All Tasks (`GET /tasks`)

Retrieves a list of all stored tasks, optionally filtered by status.

- **URL**: `/tasks`
- **Method**: `GET`
- **Query Parameters**:
  - `status` *(optional)*: Filter tasks by state (e.g. `/tasks?status=pending`)

#### Successful Response (`200 OK`)
```json
{
  "count": 2,
  "tasks": [
    {
      "id": 1,
      "title": "Configure Flask CRUD routes",
      "description": "Implement POST, GET, PUT, and DELETE with status codes",
      "status": "pending",
      "created_at": "2026-09-29T12:00:00.000000+00:00",
      "updated_at": "2026-09-29T12:00:00.000000+00:00"
    },
    {
      "id": 2,
      "title": "Document API in README",
      "description": "Provide cURL and Postman instructions",
      "status": "completed",
      "created_at": "2026-09-29T12:05:00.000000+00:00",
      "updated_at": "2026-09-29T12:10:00.000000+00:00"
    }
  ]
}
```

---

### 3.3 Retrieve Single Task by ID (`GET /tasks/<id>`)

Retrieves a single task identified by its unique ID.

- **URL**: `/tasks/<id>`
- **Method**: `GET`
- **URL Parameters**:
  - `<id>`: Integer or string task identifier (e.g., `1`)

#### Successful Response (`200 OK`)
```json
{
  "id": 1,
  "title": "Configure Flask CRUD routes",
  "description": "Implement POST, GET, PUT, and DELETE with status codes",
  "status": "pending",
  "created_at": "2026-09-29T12:00:00.000000+00:00",
  "updated_at": "2026-09-29T12:00:00.000000+00:00"
}
```

#### Error Response (`404 Not Found`)
```json
{
  "error": "Not Found",
  "message": "Task with id '999' not found"
}
```

---

### 3.4 Update Task by ID (`PUT /tasks/<id>`)

Updates one or more fields of an existing task.

- **URL**: `/tasks/<id>`
- **Method**: `PUT`
- **Headers**:
  - `Content-Type: application/json`
- **URL Parameters**:
  - `<id>`: Integer or string task identifier

#### Request Body Example
```json
{
  "title": "Configure Flask CRUD routes (Refactored)",
  "status": "completed",
  "description": "All endpoints implemented and status codes verified"
}
```

#### Successful Response (`200 OK`)
```json
{
  "message": "Task updated successfully",
  "task": {
    "id": 1,
    "title": "Configure Flask CRUD routes (Refactored)",
    "description": "All endpoints implemented and status codes verified",
    "status": "completed",
    "created_at": "2026-09-29T12:00:00.000000+00:00",
    "updated_at": "2026-09-29T12:15:00.000000+00:00"
  }
}
```

#### Error Responses
- **`400 Bad Request`** (Empty title provided):
  ```json
  {
    "error": "Bad Request",
    "message": "Field 'title' cannot be empty"
  }
  ```
- **`404 Not Found`** (Task ID does not exist):
  ```json
  {
    "error": "Not Found",
    "message": "Task with id '999' not found"
  }
  ```

---

### 3.5 Delete Task by ID (`DELETE /tasks/<id>`)

Deletes an existing task from storage.

- **URL**: `/tasks/<id>`
- **Method**: `DELETE`
- **URL Parameters**:
  - `<id>`: Integer or string task identifier

#### Successful Response (`200 OK`)
```json
{
  "id": "1",
  "message": "Task 1 deleted successfully"
}
```

#### Error Response (`404 Not Found`)
```json
{
  "error": "Not Found",
  "message": "Task with id '999' not found"
}
```

---

## 4. HTTP Status Code Handling Reference

| Status Code | Reason Phrase | Trigger Condition |
|:---|:---|:---|
| **`200 OK`** | Success | Standard successful response for `GET`, `PUT`, and `DELETE` operations. |
| **`201 Created`** | Created | Returned upon successful task creation via `POST /tasks`. |
| **`400 Bad Request`** | Client Error | Missing required JSON body, missing/empty `title`, or malformed input payload. |
| **`404 Not Found`** | Resource Missing | Target task identifier does not exist in storage during `GET`, `PUT`, or `DELETE`. |
| **`405 Method Not Allowed`** | Verb Unsupported | Invoking unsupported HTTP verbs on defined paths (e.g. `DELETE /tasks`). |
| **`500 Internal Error`** | Server Error | Uncaught server-side exceptions (handled cleanly returning JSON error body). |

---

## 5. Testing with cURL

Execute these commands in your shell to verify all CRUD endpoints:

### Step 1: Create a Task (`POST /tasks` -> 201)
```bash
curl -X POST http://127.0.0.1:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Complete Week 03 REST API",
    "description": "Implement CRUD endpoints and status codes",
    "status": "pending"
  }'
```

### Step 2: Retrieve All Tasks (`GET /tasks` -> 200)
```bash
curl -X GET http://127.0.0.1:5000/tasks
```

### Step 3: Retrieve Single Task (`GET /tasks/1` -> 200)
```bash
curl -X GET http://127.0.0.1:5000/tasks/1
```

### Step 4: Test Not Found Handling (`GET /tasks/999` -> 404)
```bash
curl -X GET http://127.0.0.1:5000/tasks/999
```

### Step 5: Update a Task (`PUT /tasks/1` -> 200)
```bash
curl -X PUT http://127.0.0.1:5000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Complete Week 03 REST API (Updated)",
    "status": "completed"
  }'
```

### Step 6: Delete a Task (`DELETE /tasks/1` -> 200)
```bash
curl -X DELETE http://127.0.0.1:5000/tasks/1
```

### Step 7: Confirm Deletion (`GET /tasks/1` -> 404)
```bash
curl -X GET http://127.0.0.1:5000/tasks/1
```

---

## 6. Testing with Postman

1. **Launch Postman** and create a new Collection named `Task Manager REST API`.
2. **Set Collection Variable**: `base_url` = `http://127.0.0.1:5000`.
3. **Add Requests**:
   - **Create Task**:
     - Method: `POST`
     - URL: `{{base_url}}/tasks`
     - Header: `Content-Type: application/json`
     - Body (raw JSON): `{"title": "Test Task", "status": "pending"}`
     - Tests tab: `pm.response.to.have.status(201);`
   - **List Tasks**:
     - Method: `GET`
     - URL: `{{base_url}}/tasks`
     - Tests tab: `pm.response.to.have.status(200);`
   - **Get Task by ID**:
     - Method: `GET`
     - URL: `{{base_url}}/tasks/1`
     - Tests tab: `pm.response.to.have.status(200);`
   - **Update Task**:
     - Method: `PUT`
     - URL: `{{base_url}}/tasks/1`
     - Header: `Content-Type: application/json`
     - Body (raw JSON): `{"status": "completed"}`
     - Tests tab: `pm.response.to.have.status(200);`
   - **Delete Task**:
     - Method: `DELETE`
     - URL: `{{base_url}}/tasks/1`
     - Tests tab: `pm.response.to.have.status(200);`
4. **Run Collection**: Click **Run Collection** to execute all tests automatically and verify status codes.

---

## 7. Automated Test Execution

Run the provided test suite using Python's built-in `unittest` runner:

```bash
cd practice/week-03-build-rest-api-endpoints-for-task-crud
python -m unittest test_routes.py
```

All 13 automated test cases validate status codes (`201`, `200`, `400`, `404`, `405`) and verify valid JSON payloads across all CRUD operations.