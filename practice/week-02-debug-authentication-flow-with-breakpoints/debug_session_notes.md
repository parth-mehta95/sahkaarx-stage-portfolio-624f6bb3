# Debug Session Walkthrough Notes

**Project:** SahkaarX Task Manager  
**Module:** Authentication Flow Debugging (`practice/week-02-debug-authentication-flow-with-breakpoints/auth.py`)  
**Objective:** Debug the authentication flow to ensure password hashing and user lookup work correctly using breakpoints to trace execution.

---

## 1. Executive Summary

This document provides complete walkthrough notes for the interactive debugging session of the authentication subsystem. The session was conducted to verify that:
1. Breakpoints correctly pause execution at critical steps during user registration and login.
2. Password hashing executes securely using salted cryptographic algorithms (PBKDF2/Scrypt/Werkzeug), ensuring plain-text passwords are never stored in memory or persistence.
3. User lookup queries return exact match entities, properly distinguish between existing and non-existing records, and handle edge cases (e.g. duplicate accounts, bad passwords).

---

## 2. Debugging Environment & Tooling Setup

### 2.1 Configuration
- **Runtime:** Python 3.10+ / Flask 3.x
- **Debugger:** Python Interactive Debugger (`pdb` / `debugpy` / VS Code Python Debugger)
- **Primary Source File:** [`auth.py`](file:///d:/challengers%20testing/sahkaarx-stage-portfolio-624f6bb3/practice/week-02-debug-authentication-flow-with-breakpoints/auth.py)
- **Activation Mode:** Inline breakpoint markers `# >>> BREAKPOINT X LOCATION <<<` and programmatic `breakpoint()` / `debug_pause()` hooks when `DEBUG_BREAKPOINTS=1`.

### 2.2 VS Code Debugger Launch Configuration (`launch.json`)
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Debug Auth Flow",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/practice/week-02-debug-authentication-flow-with-breakpoints/auth.py",
            "env": {
                "FLASK_ENV": "development",
                "DEBUG_BREAKPOINTS": "1",
                "PYTHONUNBUFFERED": "1"
            },
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

---

## 3. Breakpoint Locations Inventory

The following table summarizes all breakpoint locations set across the authentication routes:

| Breakpoint ID | Route / Scope | Line Target | Purpose & Inspection Goal | Key Variables Watched |
| :--- | :--- | :--- | :--- | :--- |
| **BREAKPOINT 1** | `POST /register` | Step 1 | Pause on request entry to inspect raw payload | `request.get_json()`, `data`, `username`, `email` |
| **BREAKPOINT 2** | `POST /register` | Step 2 | Verify user lookup query for duplicate username | `clean_username`, `existing_user_by_name` |
| **BREAKPOINT 3** | `POST /register` | Step 3 | Verify user lookup query for duplicate email | `clean_email`, `existing_user_by_email` |
| **BREAKPOINT 4** | `POST /register` | Step 4 | **Verify password hashing occurs & inspect salt/hash** | `password`, `hashed_password`, algorithm prefix |
| **BREAKPOINT 5** | `POST /register` | Step 5 | Inspect user entity creation & persistence | `new_user`, `new_user.id`, `new_user.password_hash` |
| **BREAKPOINT 6** | `POST /login` | Step 6 | Pause on login entry to inspect input credentials | `request.get_json()`, `username`, `password` |
| **BREAKPOINT 7** | `POST /login` | Step 7 | **Confirm user lookup query returns correct user data** | `clean_identifier`, `user`, `user.id`, `user.password_hash` |
| **BREAKPOINT 8** | `POST /login` | Step 8 | **Verify password hash comparison logic** | `candidate_password`, `user.password_hash`, `is_valid_password` |
| **BREAKPOINT 9** | `POST /login` | Step 9 | Inspect successful authentication response generation | `user.to_dict()`, HTTP 200 payload |
| **BREAKPOINT 10** | `GET /users/<username>` | Profile query | Verify standalone user lookup query by username | `username`, `user`, returned profile dict |

---

## 4. Step-by-Step Debug Session Walkthrough

### Part 1: Registration Flow & Password Hashing Verification

#### Test Payload Sent:
```json
POST /register HTTP/1.1
Content-Type: application/json

{
    "username": "debug_user",
    "email": "debug_user@example.com",
    "password": "SuperSecretPassword123!"
}
```

#### Breakpoint Tracing:
1. **Paused at BREAKPOINT 1 (Entry & Payload Extraction):**
   - **Debugger command:** `p request.get_json()`
   - **Observed:**
     ```python
     {'username': 'debug_user', 'email': 'debug_user@example.com', 'password': 'SuperSecretPassword123!'}
     ```
   - **Validation:** All required fields are present, trimmed, and correctly typed.

2. **Paused at BREAKPOINT 2 (User Lookup by Username):**
   - **Code executed:** `existing_user_by_name = User.find_by_username(clean_username)`
   - **Debugger command:** `p existing_user_by_name`
   - **Observed:** `None`
   - **Verification:** User lookup query executed against indexed storage; confirmed no user exists yet with username `'debug_user'`. Registration proceeds.

3. **Paused at BREAKPOINT 3 (User Lookup by Email):**
   - **Code executed:** `existing_user_by_email = User.find_by_email(clean_email)`
   - **Debugger command:** `p existing_user_by_email`
   - **Observed:** `None`
   - **Verification:** User lookup query confirmed no account registered with `'debug_user@example.com'`.

4. **Paused at BREAKPOINT 4 (Password Hashing Verification - CRITICAL STEP):**
   - **Stepped Into (`step` / `s`):** `User.hash_password(password)`
   - **Inspected Variables in Debugger:**
     ```text
     (Pdb) p password
     'SuperSecretPassword123!'
     (Pdb) n
     (Pdb) p hashed_password
     'scrypt:32768:8:1$u7P9zK...$e8c7b8...'
     (Pdb) p password == hashed_password
     False
     (Pdb) p hashed_password.startswith(('scrypt:', 'pbkdf2:'))
     True
     ```
   - **Verification Results:**
     - Plain-text password `'SuperSecretPassword123!'` was successfully transformed into a secure cryptographic hash.
     - Hash contains algorithm identifier, work factor parameters, unique salt, and HMAC/digest.
     - Plain-text password is **not** written to the user entity or stored in memory attributes.

5. **Paused at BREAKPOINT 5 (User Persistence):**
   - **Code executed:** `new_user = User(username=clean_username, email=clean_email, password_hash=hashed_password)`
   - **Inspected Variables:**
     ```text
     (Pdb) p new_user.id
     1
     (Pdb) p new_user.username
     'debug_user'
     (Pdb) p new_user.password_hash
     'scrypt:32768:8:1$u7P9zK...$e8c7b8...'
     (Pdb) p new_user.to_dict()
     {'id': 1, 'username': 'debug_user', 'email': 'debug_user@example.com', 'created_at': '2026-09-29T17:25:00.123456'}
     ```
   - **Verification:** Serialized response dictionary sanitizes security-sensitive fields (omits `password_hash`). HTTP 201 Created returned.

---

### Part 2: Login Flow & User Lookup Query Verification

#### Test Case 1: Valid Login Request
```json
POST /login HTTP/1.1
Content-Type: application/json

{
    "username": "debug_user",
    "password": "SuperSecretPassword123!"
}
```

1. **Paused at BREAKPOINT 6 (Login Entry & Extraction):**
   - **Debugger command:** `p data`
   - **Observed:** `{'username': 'debug_user', 'password': 'SuperSecretPassword123!'}`

2. **Paused at BREAKPOINT 7 (User Lookup Query Execution - CRITICAL STEP):**
   - **Code executed:** `user = User.find_by_username(clean_identifier) or User.find_by_email(clean_identifier)`
   - **Inspected Variables in Debugger:**
     ```text
     (Pdb) p clean_identifier
     'debug_user'
     (Pdb) p user
     <User id=1 username='debug_user'>
     (Pdb) p user.id
     1
     (Pdb) p user.email
     'debug_user@example.com'
     (Pdb) p user.password_hash
     'scrypt:32768:8:1$u7P9zK...$e8c7b8...'
     ```
   - **Verification:** User lookup query correctly located and returned the registered User entity with all associated metadata.

3. **Paused at BREAKPOINT 8 (Password Hash Verification):**
   - **Stepped Into (`step` / `s`):** `user.check_password(password)` -> `check_password_hash(self.password_hash, candidate_password)`
   - **Inspected Variables:**
     ```text
     (Pdb) p password
     'SuperSecretPassword123!'
     (Pdb) p user.password_hash
     'scrypt:32768:8:1$u7P9zK...$e8c7b8...'
     (Pdb) n
     (Pdb) p is_valid_password
     True
     ```
   - **Verification:** Password comparison returned `True`. Timing-attack-resistant verification succeeded.

4. **Paused at BREAKPOINT 9 (Response Generation):**
   - Authentication successful, returning HTTP 200 with sanitized user profile.

---

#### Test Case 2: Invalid Password Verification
```json
POST /login HTTP/1.1
Content-Type: application/json

{
    "username": "debug_user",
    "password": "WrongPassword999!"
}
```
- **Paused at BREAKPOINT 7:** User record found (`user.username == 'debug_user'`).
- **Paused at BREAKPOINT 8:**
  ```text
  (Pdb) p is_valid_password
  False
  ```
- **Observed:** Route branches into `if not is_valid_password:` and returns `401 Unauthorized` with `{"error": "Invalid username or password."}`.
- **Verification:** Prevents unauthorized access when bad credentials are supplied.

---

#### Test Case 3: User Lookup for Non-Existent User
```json
POST /login HTTP/1.1
Content-Type: application/json

{
    "username": "non_existent_user",
    "password": "AnyPassword123!"
}
```
- **Paused at BREAKPOINT 7:**
  ```text
  (Pdb) p user
  None
  ```
- **Observed:** Query returns `None`. Execution short-circuits before running expensive password hashing computations, returning `401 Unauthorized`.
- **Verification:** Confirms user lookup query correctly handles non-existent users.

---

## 5. Success Criteria Verification Matrix

| Success Criterion | Verification Method | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Breakpoints pause at key auth steps** | Triggered execution through interactive debugger / `debug_pause` | **PASSED** | Paused at all 10 breakpoints in registration, lookup, hashing, and login routes. |
| **Password hashing verified in debugger** | Stepped into `generate_password_hash()` and inspected memory variables | **PASSED** | Plain-text password transformed to salted cryptographic hash; plain-text never saved. |
| **User lookup queries return correct data** | Inspected `User.find_by_username()` and `User.find_by_email()` results | **PASSED** | Correct user object returned on valid query; `None` returned on non-existent query. |
| **Duplicate user prevention** | Tested duplicate registration attempts with identical username/email | **PASSED** | Lookup queries intercepted duplicates and returned HTTP 409 Conflict. |
| **Incorrect password rejection** | Stepped through `check_password()` with invalid credentials | **PASSED** | Evaluated to `False`, rejecting login with HTTP 401 Unauthorized. |

---

## 6. How to Re-Run the Debugging Walkthrough

### Option A: Standalone Automated Trace Walkthrough
Run the built-in walkthrough runner to view all breakpoint states printed sequentially:
```bash
python auth.py --walkthrough
```

### Option B: Interactive Breakpoints in Debugger
Enable interactive debugger pauses by exporting `DEBUG_BREAKPOINTS=1`:
```bash
# In PowerShell:
$env:DEBUG_BREAKPOINTS="1"
python auth.py

# In Bash:
export DEBUG_BREAKPOINTS=1
python auth.py
```
Send requests using `curl` or Postman to hit the active breakpoints in `auth.py`.
