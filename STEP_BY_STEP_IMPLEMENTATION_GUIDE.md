# Banking Web Application — Step-by-Step Implementation Guide

> **Document Type:** Implementation Instructions (Plain English — Logic & Approach, No Code)
> **References:** [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)
> **Technology Stack:** HTML + Bootstrap · Python Flask · SQLite

---

## Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Backend Implementation](#2-backend-implementation)
3. [Frontend Implementation](#3-frontend-implementation)
4. [Integration Steps](#4-integration-steps)
5. [Validation Rules](#5-validation-rules)
6. [Testing](#6-testing)
7. [Deployment](#7-deployment)

---

## 1. Environment Setup

### 1.1 Prerequisites Check

Before writing a single line of code, confirm that the following tools are installed on the machine:

- **Python 3.11 or above** — the runtime for the Flask application.
- **pip** — Python's package manager, used to install Flask and other libraries.
- **A code editor** (e.g., VS Code) — for editing Python and HTML files.
- **A terminal / command prompt** — all commands are run here.

Verify each by asking the terminal to print the version number of Python and pip. If either is missing, install Python from python.org; pip is bundled with it.

---

### 1.2 Create the Project Folder Structure

Create the top-level project directory and the two primary sub-folders inside it:

- `FRONTEND/` — will hold all HTML template files.
- `BACKEND/` — will hold all Python source files and the database.
- `tests/` — will hold all automated test files.

Inside `FRONTEND/`, create a sub-folder called `templates/`. Flask will look in this folder when rendering HTML pages.

This mirrors the folder structure described in [`IMPLEMENTATION_PLAN.md § 4`](IMPLEMENTATION_PLAN.md).

---

### 1.3 Create and Activate a Virtual Environment

A virtual environment is an isolated Python workspace. It keeps the project's dependencies separate from any other Python projects on the machine.

**How to think about it:** Imagine a sealed box that contains only the packages this project needs. When you activate it, your terminal works inside that box.

Steps:

1. Navigate into the project root in the terminal.
2. Ask Python to create a virtual environment folder, typically named `venv`, inside the project directory.
3. Activate the virtual environment using the activation command for your operating system.
   - On **Windows**, run the activate script inside `venv\Scripts\`.
   - On **macOS/Linux**, source the activate script inside `venv/bin/`.
4. Once activated, the terminal prompt changes to show `(venv)` — this confirms you are inside the isolated environment.

> **Important:** Always activate the virtual environment before running any Flask commands or installing packages. Never commit the `venv/` folder to version control.

---

### 1.4 Create the Requirements File and Install Dependencies

Create a plain text file called `requirements.txt` inside the `BACKEND/` folder. List the following packages, one per line:

| Package | Purpose |
|---|---|
| `Flask` | The web framework — handles routing, templates, and sessions |
| `Werkzeug` | Provides password hashing utilities used for secure credential storage |
| `pytest` | The testing framework for writing and running automated tests |

Once the file is saved, tell pip to read it and install everything listed. This single command installs all three packages into the active virtual environment.

---

### 1.5 Flask Setup and Configuration

Flask needs one environment variable to know which file to start from:

- `FLASK_APP` — set this to point at `BACKEND/app.py` (the main application file you will create next).
- `FLASK_ENV` — set this to `development` while building the app. This enables debug mode, which shows detailed error pages and auto-restarts the server when you save a file.

You can set these variables in the terminal each time, or create a `.flaskenv` file at the project root so Flask reads them automatically on startup.

> **Security note:** Never set `FLASK_ENV=development` in a production environment.

---

## 2. Backend Implementation

### 2.1 Create the Flask Application (`app.py`)

`app.py` is the entry point — the first file Flask reads when it starts.

**What it should do:**

1. **Create the Flask app instance.** Tell Flask where to find templates by pointing it at the `FRONTEND/templates/` folder, which is outside the default location.
2. **Set a secret key.** Flask needs a secret key to sign session cookies securely. Use a long, random string. Without this, sessions will not work.
3. **Register all routes.** Define the URL paths the application responds to: `/`, `/login`, `/logout`, `/dashboard`, `/deposit`, `/withdraw`.
4. **Call the database initialisation function** on startup so the database and tables exist before the first request arrives.

Think of `app.py` as the traffic controller — it receives every incoming HTTP request and decides which function should handle it.

---

### 2.2 Database Layer (`database.py`)

This module is the only part of the application that talks directly to SQLite.

**What it should do:**

1. **Store the database file path** as a constant so every other module imports it from one place.
2. **Provide a `get_connection()` function** that opens a connection to the SQLite file and returns it. Configure the connection to return rows as dictionary-like objects so that columns can be accessed by name rather than by index.
3. **Provide a `close_connection()` function** (or use Python's context manager pattern) so connections are always closed after use — this prevents resource leaks.
4. **Provide an `init_db()` function** that creates the `customers` table and the `transactions` table if they do not already exist, then inserts one demo customer if the table is empty.

> **Key principle:** No other module should contain raw SQL. All SQL lives here. Other modules call named functions like `get_customer_by_username()` or `update_balance()`.

---

### 2.3 Seeding the Database (`seed.py`)

Seeding means inserting initial data so the application has something to work with from the start.

**What it should do:**

1. Call `init_db()` from `database.py` to create the tables.
2. Create one demo customer record with a username (e.g., `demo_user`), a **hashed** password (use Werkzeug's `generate_password_hash`), a full name, and a starting balance (e.g., 1000.00).
3. Check whether the demo customer already exists before inserting — running the script twice should not create duplicate records.

Run this script once manually before starting the app for the first time. After that, `init_db()` in `app.py` handles subsequent starts.

---

### 2.4 Authentication Module (`auth.py`)

This module owns everything related to identity: proving who a user is and managing their session.

**What it should contain:**

#### `verify_login(username, password)` function

- Look up the customer record in the database by username.
- If no record is found, return a failure result immediately — do not reveal whether the username exists or the password was wrong (generic error).
- If a record is found, use Werkzeug's `check_password_hash` to compare the submitted password against the stored hash.
- If the hash matches, return a success result along with the customer's data. Otherwise return failure.

#### `login_required` decorator

- A decorator is a wrapper you apply to route functions. When a route is decorated with `login_required`, the decorator runs first.
- It checks whether `customer_id` exists in Flask's session object.
- If the session key is present, the original route function runs normally.
- If the session key is missing (user not logged in), the decorator redirects the request to `/login` immediately.
- Apply this decorator to every route that should not be accessible to unauthenticated users: `/dashboard`, `/deposit`, `/withdraw`.

#### `create_session(customer_id)` function

- Store the `customer_id` value inside Flask's session dictionary.
- Flask automatically encrypts and signs this cookie using the app's secret key.

#### `destroy_session()` function

- Clear all data from Flask's session dictionary.
- This effectively logs the user out — their cookie becomes empty and meaningless.

---

### 2.5 Routes and Controllers (`app.py`)

Each route is a function that handles one URL. The logic for each:

#### `GET /` (Root)
- Redirect immediately to `/login`. The root URL should never show a blank page.

#### `GET + POST /login`
- **GET:** Render the login page template. If the user is already logged in (session exists), redirect to `/dashboard` instead.
- **POST:** Read the username and password from the submitted form. Call `verify_login()`. If successful, call `create_session()` and redirect to `/dashboard`. If unsuccessful, re-render the login page with a generic error message: "Invalid username or password."

#### `GET /logout`
- Call `destroy_session()` to clear the session.
- Redirect to `/login`.
- This route does not need `login_required` — logging out when not logged in should just redirect cleanly.

#### `GET /dashboard`
- Requires `login_required`.
- Read the `customer_id` from the session.
- Fetch the customer's name and current balance from the database.
- Render the dashboard template, passing the name and balance as template variables.
- Also pass any pending flash messages to the template.

#### `GET + POST /deposit`
- Requires `login_required`.
- **GET:** Render the deposit form template.
- **POST:** Read the amount from the form, pass it to the deposit service function. If successful, set a success flash message and redirect to `/dashboard`. If validation fails, set an error flash message and re-render the deposit form.

#### `GET + POST /withdraw`
- Requires `login_required`.
- **GET:** Render the withdraw form template.
- **POST:** Read the amount from the form, pass it to the withdrawal service function. If successful, set a success flash message and redirect to `/dashboard`. If validation fails (bad amount or insufficient funds), set an error flash message and re-render the withdraw form.

---

### 2.6 Transaction Services (`transactions.py`)

This module contains the business logic for deposits and withdrawals. It does not handle HTTP — it only processes data.

#### `deposit(customer_id, amount)` function

Logic steps:
1. Ensure the amount is a valid number (can be converted from string to float/decimal).
2. Ensure the amount is greater than zero.
3. Fetch the customer's current balance from the database.
4. Calculate the new balance by adding the amount.
5. Update the balance in the `customers` table.
6. Insert a record into the `transactions` table with type "deposit", the amount, and the current timestamp.
7. Return a success result.

If steps 1 or 2 fail, return an error result with a descriptive message — do not touch the database.

#### `withdraw(customer_id, amount)` function

Logic steps:
1. Ensure the amount is a valid number.
2. Ensure the amount is greater than zero.
3. Fetch the customer's current balance from the database.
4. Check that the balance is greater than or equal to the requested amount (insufficient funds check).
5. Calculate the new balance by subtracting the amount.
6. Update the balance in the `customers` table.
7. Insert a record into the `transactions` table with type "withdrawal", the amount, and the current timestamp.
8. Return a success result.

If steps 1, 2, or 4 fail, return an error result — do not touch the database.

---

### 2.7 Session Management

Flask's session is a dictionary stored as an encrypted cookie in the browser.

**Key rules to follow:**

- **On login:** Write `customer_id` (and optionally `customer_name`) into the session dictionary after a successful credential check.
- **On every protected request:** The `login_required` decorator reads `customer_id` from the session. If it's there, the user is authenticated. If it's missing, redirect to login.
- **On logout:** Call Flask's `session.clear()` or pop individual keys to remove all session data. The browser's cookie becomes empty.
- **Secret key:** The secret key in `app.py` must be a strong, unpredictable string. If changed, all existing sessions are immediately invalidated.

---

### 2.8 Error Handling

**Application-level errors** (wrong input, failed operations) are communicated back to the user through Flask's flash message system:

- After a failed deposit or withdrawal, call Flask's `flash()` function with an error message and a category (e.g., `"error"`).
- After a successful operation, call `flash()` with a success message (e.g., `"error"` or `"success"`).
- In every template, check for flash messages and display them prominently at the top of the page.

**HTTP error pages:**

- Create a custom handler for `404 Not Found` — render a friendly "page not found" message.
- Create a custom handler for `500 Internal Server Error` — render a friendly "something went wrong" message and log the error.

**Never expose** raw Python tracebacks to the browser in production. Debug mode (which shows tracebacks) must only be on during development.

---

## 3. Frontend Implementation

### 3.1 Shared Layout Principles

All HTML pages should follow the same Bootstrap layout pattern:

- Use the Bootstrap CDN `<link>` tag in the `<head>` of every page to load Bootstrap's CSS.
- Wrap all page content in a Bootstrap `container` div to keep content centred and padded.
- Use Bootstrap's grid system (`row` and `col` classes) to arrange elements responsively.
- Use Bootstrap utility classes for spacing (`mt-`, `mb-`, `p-`), colour (`text-danger`, `text-success`), and typography.

Flash messages should appear at the top of the content area, inside a Bootstrap `alert` component. Use the alert's colour variant to distinguish between success (green) and error (red) messages.

---

### 3.2 Login Page (`login.html`)

**Purpose:** Collect the customer's username and password and submit them to the backend.

**What to include:**

- A centred card or panel that contains the login form.
- A bank logo or application title at the top.
- A text input field for **username** — the `name` attribute must match what Flask reads on the backend (`request.form['username']`).
- A password input field for **password** — use `type="password"` so the characters are masked.
- A "Login" submit button styled with Bootstrap's button class.
- An area above the form to display error flash messages (e.g., "Invalid username or password").
- The form's `action` attribute must point to `/login` and the `method` must be `POST`.

**What NOT to include:** No JavaScript validation — all validation happens on the server.

---

### 3.3 Dashboard Page (`dashboard.html`)

**Purpose:** Show the customer their account overview and provide navigation to all actions.

**What to include:**

- A navigation bar at the top with the application name and a "Logout" link pointing to `/logout`.
- A welcome message that includes the customer's name (passed as a template variable by Flask).
- A prominent balance display — show the balance formatted as currency (e.g., `$1,000.00`). Jinja2's `format` filter can handle number formatting.
- Two action buttons or links: "Deposit" (links to `/deposit`) and "Withdraw" (links to `/withdraw`).
- A flash message display area that shows any success or error messages from the previous operation.

**Template variable wiring:** Flask passes `customer_name` and `balance` to this template. Use Jinja2's `{{ variable }}` syntax to inject them into the HTML.

---

### 3.4 Deposit Page (`deposit.html`)

**Purpose:** Allow the customer to enter an amount to deposit.

**What to include:**

- A heading: "Deposit Funds".
- A number input field for the amount. Set `min="0.01"` and `step="0.01"` as HTML attributes to guide the browser, but remember that server-side validation is the real gate.
- A "Deposit" submit button.
- A "Back to Dashboard" link.
- A flash message display area for errors (e.g., "Amount must be greater than zero").
- The form's `action` must point to `/deposit` and the `method` must be `POST`.

---

### 3.5 Withdraw Page (`withdraw.html`)

**Purpose:** Allow the customer to enter an amount to withdraw.

**What to include:**

- A heading: "Withdraw Funds".
- The current balance displayed for reference (pass it from Flask so the customer knows their limit).
- A number input field for the amount, with the same `min` and `step` attributes as the deposit form.
- A "Withdraw" submit button.
- A "Back to Dashboard" link.
- A flash message display area for errors (e.g., "Insufficient funds").
- The form's `action` must point to `/withdraw` and the `method` must be `POST`.

---

### 3.6 Bootstrap Layout Rules (Applies to All Pages)

| Rule | Reason |
|---|---|
| Use `container` or `container-fluid` as the outermost wrapper | Provides consistent margins and max-width |
| Use `row` and `col-md-*` for multi-column layouts | Makes the layout responsive on smaller screens |
| Use `form-control` on all input fields | Gives inputs consistent Bootstrap styling |
| Use `btn btn-primary` on submit buttons | Consistent, accessible button appearance |
| Use `alert alert-danger` for error messages | Clear visual distinction for errors |
| Use `alert alert-success` for success messages | Clear visual distinction for confirmations |
| Use `navbar navbar-expand-lg` for the top navigation | Collapses correctly on mobile devices |

---

## 4. Integration Steps

### 4.1 Connect Frontend Templates to Flask Routes

Flask uses **Jinja2** as its template engine. This is how the frontend and backend are wired together:

1. **Template folder registration:** When creating the Flask app, pass the `template_folder` parameter pointing to `FRONTEND/templates/`. This tells Flask where to find HTML files when `render_template()` is called.

2. **Rendering a template:** In each route handler, call `render_template('page_name.html', variable=value)`. The named variables become available inside the HTML template as `{{ variable }}`.

3. **Form submission wiring:** Every HTML form's `action` attribute must exactly match a Flask route URL. The `method` attribute must be `POST` for any form that sends data. Flask reads submitted values using `request.form['field_name']`, where `field_name` matches the `name` attribute on the HTML input.

4. **URL generation with `url_for`:** Instead of hard-coding URLs like `/dashboard`, use Jinja2's `{{ url_for('dashboard') }}` syntax in templates. This generates the correct URL even if routes are renamed.

5. **Flash message flow:** The backend calls `flash('message', 'category')`. The template reads pending flash messages using Jinja2's `get_flashed_messages(with_categories=True)` and renders them inside Bootstrap alert components.

---

### 4.2 Connect Flask to SQLite

1. **Database file location:** Store `banking.db` inside the `BACKEND/` folder. In `database.py`, compute its absolute path using Python's `os.path` so it works regardless of which directory Flask is launched from.

2. **Connection per request pattern:** Open a database connection at the start of a request and close it when the request ends. Flask provides `g` (the application context object) and `teardown_appcontext` to manage this cleanly — store the connection on `g` and register a teardown function that closes it.

3. **Parameterised queries:** Always pass user-supplied values (username, amounts) as parameters to SQL queries using the `?` placeholder — never by string concatenation. This prevents SQL injection attacks.

4. **Row factory:** Configure the SQLite connection's `row_factory` to return rows that behave like dictionaries. This allows accessing a column by name (e.g., `row['balance']`) instead of by position (e.g., `row[2]`).

5. **Transaction control:** For any operation that involves multiple writes (e.g., updating the balance AND inserting a transaction log record), wrap both writes in a single database transaction. If either write fails, roll back both — the database should never be left in a half-updated state.

---

## 5. Validation Rules

### 5.1 Login Validation

| Rule | Where enforced | Behaviour on failure |
|---|---|---|
| Username field must not be empty | Backend (`auth.py`) | Re-render login page with error message |
| Password field must not be empty | Backend (`auth.py`) | Re-render login page with error message |
| Username must exist in the database | Backend (`auth.py`) | Return generic "Invalid username or password" — do not indicate which field was wrong |
| Password must match stored hash | Backend (`auth.py`) | Return generic "Invalid username or password" |

> **Why generic errors?** Specific messages like "Username not found" tell an attacker which usernames are valid. A single generic message prevents this information leak.

---

### 5.2 Balance Validation

| Rule | Where enforced | Behaviour on failure |
|---|---|---|
| Balance must never go below zero | Backend (`transactions.py`) | Reject the withdrawal before any database write |
| Balance must be readable before any transaction | Backend (`transactions.py`) | If balance cannot be fetched, abort the transaction and return an error |

---

### 5.3 Deposit Validation

| Rule | Where enforced | Behaviour on failure |
|---|---|---|
| Amount field must not be empty | Backend (`transactions.py`) | Return error: "Please enter an amount" |
| Amount must be a valid number | Backend (`transactions.py`) | Return error: "Amount must be a valid number" |
| Amount must be greater than zero | Backend (`transactions.py`) | Return error: "Amount must be greater than zero" |
| Amount must not exceed a reasonable maximum (optional safeguard) | Backend (`transactions.py`) | Return error: "Amount exceeds the maximum allowed per transaction" |

---

### 5.4 Withdrawal Validation

| Rule | Where enforced | Behaviour on failure |
|---|---|---|
| Amount field must not be empty | Backend (`transactions.py`) | Return error: "Please enter an amount" |
| Amount must be a valid number | Backend (`transactions.py`) | Return error: "Amount must be a valid number" |
| Amount must be greater than zero | Backend (`transactions.py`) | Return error: "Amount must be greater than zero" |
| Amount must not exceed the current balance | Backend (`transactions.py`) | Return error: "Insufficient funds. Your current balance is $X.XX" |

> **Validation order matters:** Always check that the value is a valid number *before* comparing it to the balance. Trying to compare a non-numeric string to a number will cause a runtime error.

---

## 6. Testing

### 6.1 Unit Tests

Unit tests verify individual functions in isolation — no HTTP requests, no real database.

**What to test in `auth.py`:**
- `verify_login()` returns success when given correct credentials.
- `verify_login()` returns failure when given a wrong password.
- `verify_login()` returns failure when given a username that does not exist.
- `create_session()` writes the correct key into the session.
- `destroy_session()` removes all keys from the session.

**What to test in `transactions.py`:**
- `deposit()` correctly adds the amount to the balance.
- `deposit()` returns an error when the amount is zero.
- `deposit()` returns an error when the amount is negative.
- `deposit()` returns an error when the amount is not a number.
- `withdraw()` correctly subtracts the amount from the balance.
- `withdraw()` returns an error when the amount exceeds the balance.
- `withdraw()` returns an error when the amount is zero.
- `withdraw()` returns an error when the amount is negative.

**How to isolate from the database:** Use a separate in-memory SQLite database for tests (`:memory:` as the path). Reset it before each test so tests do not interfere with each other.

---

### 6.2 Integration Tests

Integration tests verify that Flask routes, business logic, and the database work together correctly end-to-end.

**What to test:**

| Scenario | Expected Result |
|---|---|
| POST `/login` with valid credentials | Redirects to `/dashboard`; session contains `customer_id` |
| POST `/login` with invalid credentials | Returns login page with error message; no session created |
| GET `/dashboard` when logged in | Returns 200 with balance visible |
| GET `/dashboard` when not logged in | Redirects to `/login` |
| POST `/deposit` with a valid amount | Redirects to `/dashboard`; balance increases |
| POST `/deposit` with zero amount | Returns deposit page with error message |
| POST `/withdraw` with a valid amount | Redirects to `/dashboard`; balance decreases |
| POST `/withdraw` with amount exceeding balance | Returns withdraw page with "Insufficient funds" error |
| GET `/logout` | Clears session; redirects to `/login` |
| GET `/deposit` when not logged in | Redirects to `/login` |

**Test client setup:** Flask provides a test client (`app.test_client()`) that simulates HTTP requests without starting a real server. Create a pytest fixture that initialises the test client with an in-memory database before the test suite runs.

---

### 6.3 Manual Testing Checklist

After the application is running locally, walk through this checklist in the browser:

**Authentication Flow**
- [ ] Navigating to `http://localhost:5000/` redirects to the login page.
- [ ] Submitting the login form with an incorrect password shows a generic error message.
- [ ] Submitting the login form with the correct credentials redirects to the dashboard.
- [ ] Navigating to `/dashboard` in a new private/incognito window (no session) redirects to login.
- [ ] Clicking "Logout" returns to the login page and the session is destroyed (back button does not re-enter the app).

**Dashboard**
- [ ] The dashboard displays the customer's name and current balance correctly.
- [ ] The "Deposit" and "Withdraw" buttons navigate to the correct forms.
- [ ] Flash messages from previous operations are visible and then disappear on page refresh.

**Deposit Flow**
- [ ] Submitting the deposit form with a valid amount increases the displayed balance on the dashboard.
- [ ] Submitting with a zero amount shows an error message and does not change the balance.
- [ ] Submitting with a negative amount shows an error message and does not change the balance.
- [ ] Submitting with non-numeric text shows an error message and does not change the balance.

**Withdrawal Flow**
- [ ] Submitting the withdrawal form with a valid amount decreases the displayed balance on the dashboard.
- [ ] Submitting an amount greater than the balance shows "Insufficient funds" and does not change the balance.
- [ ] Submitting with a zero or negative amount shows an appropriate error.

**Responsiveness**
- [ ] All pages render correctly at desktop width (1280px).
- [ ] All pages render correctly at mobile width (375px) — forms stack vertically, navbar collapses.

---

## 7. Deployment

### 7.1 Run Locally

Follow these steps every time you want to start the development server:

1. Open a terminal and navigate to the project root directory.
2. Activate the virtual environment (`venv`).
3. If running for the first time, run `seed.py` to initialise the database and insert the demo customer.
4. Set the `FLASK_APP` environment variable to `BACKEND/app.py`.
5. Set the `FLASK_ENV` environment variable to `development`.
6. Run `flask run` to start the development server.
7. Open a browser and navigate to `http://localhost:5000`.

The development server will automatically reload when you save changes to Python files.

---

### 7.2 Stopping and Restarting

- Press `Ctrl + C` in the terminal to stop the Flask development server.
- To reset the database to its original state, delete `BACKEND/banking.db` and re-run `seed.py`.

---

### 7.3 Production Considerations

The Flask development server (`flask run`) is **not suitable for production**. It is single-threaded, not hardened against attacks, and not designed for high traffic. The following changes must be made before deploying to a real environment:

| Concern | Development Approach | Production Approach |
|---|---|---|
| **Web server** | Flask built-in dev server | Gunicorn or uWSGI behind Nginx |
| **Debug mode** | `FLASK_ENV=development` (debug on) | `FLASK_ENV=production` (debug off) |
| **Secret key** | Hardcoded string in source code | Read from an environment variable or secrets manager |
| **Database** | SQLite file on local disk | PostgreSQL or MySQL with connection pooling |
| **HTTPS** | Plain HTTP on localhost | TLS certificate via Nginx or a load balancer |
| **Dependency pinning** | Loose versions in `requirements.txt` | Pinned versions (`Flask==3.0.1`) for reproducibility |
| **Error logging** | Printed to terminal | Centralised logging service (e.g., Datadog, CloudWatch) |
| **Static assets** | Served by Flask | Served by Nginx or a CDN |

> **Minimum before any live deployment:** Turn off debug mode, move the secret key to an environment variable, and place the app behind a proper web server process manager.

---

### 7.4 CI/CD Pipeline Awareness

The project includes a GitHub Actions workflow file at `.github/workflows/banking-app-ci.yml`. It runs automatically on every push to `main` or any `feature/*` branch. It will:

1. Check out the code.
2. Set up Python 3.11.
3. Install dependencies from `BACKEND/requirements.txt`.
4. Run `pytest` against the `tests/` directory.

**What this means for development:** All tests in `tests/test_app.py` must pass before merging into `main`. Write tests as you build each feature — do not leave testing until the end.

---

*End of Step-by-Step Implementation Guide — Logic and approach only. No production code is included in this document.*
