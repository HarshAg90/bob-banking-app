# Banking Web Application — Implementation Plan

> **Document Type:** High-Level Planning  
> **Technology Stack:** HTML + Bootstrap (Frontend) · Python Flask (Backend) · SQLite (Database)  
> **Status:** Draft — Pending Review

---

## 1. Solution Overview

### Objective

Build a simple, browser-based retail banking application that allows customers to securely log in, view their account balance, deposit funds, withdraw funds, and log out. The application serves as a self-contained demonstration of a three-tier web architecture.

### Scope

| In Scope | Out of Scope |
|---|---|
| Customer authentication (login / logout) | User registration / self-service sign-up |
| Account balance display | Multi-account support per customer |
| Deposit and withdrawal transactions | Transfers between accounts |
| Session management | Password reset / email notifications |
| SQLite-backed persistence | Production database (PostgreSQL, MySQL) |
| Local development deployment | Cloud hosting / containerisation |

### Users

| Actor | Description |
|---|---|
| **Bank Customer** | An existing account holder who logs in to perform basic account operations |

### Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-01 | A customer must be able to log in with a username and password |
| FR-02 | An authenticated customer must see a dashboard with their account balance |
| FR-03 | An authenticated customer must be able to deposit a positive monetary amount |
| FR-04 | An authenticated customer must be able to withdraw a positive monetary amount, subject to sufficient funds |
| FR-05 | An authenticated customer must be able to log out, ending their session |
| FR-06 | Unauthenticated users must be redirected to the login page |

### Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | Passwords must be stored as hashed values — never plain text |
| NFR-02 | Session tokens must be invalidated on logout |
| NFR-03 | All user-facing pages must be responsive (Bootstrap grid) |
| NFR-04 | Invalid login attempts must return a generic error (no account enumeration) |
| NFR-05 | The application must start with a single command (`flask run`) |
| NFR-06 | The codebase must be structured to allow automated testing via `pytest` |

### Assumptions

- One pre-seeded customer account is sufficient for the demonstration.
- The application runs on `localhost` only; no HTTPS or reverse proxy is required.
- Bootstrap is loaded from a CDN; no local asset pipeline is needed.
- SQLite is acceptable for persistence; data durability under concurrent load is not a concern.
- Python 3.11 and Flask are available in the target environment.

---

## 2. High-Level Architecture

### Architecture Diagram

```
┌──────────────────────────────────────────────┐
│                   BROWSER                    │
│                                              │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  │
│  │  Login   │  │ Dashboard │  │ Deposit/ │  │
│  │  Page    │  │   Page    │  │ Withdraw │  │
│  └────┬─────┘  └─────┬─────┘  └────┬─────┘  │
│       │  HTML Forms  │             │         │
└───────┼──────────────┼─────────────┼─────────┘
        │  HTTP Request (POST/GET)   │
        ▼                            ▼
┌──────────────────────────────────────────────┐
│              BACKEND  (Flask)                │
│                                              │
│  ┌─────────────────────────────────────────┐ │
│  │              Route Layer                │ │
│  │  /login  /logout  /dashboard            │ │
│  │  /deposit  /withdraw                    │ │
│  └───────────────┬─────────────────────────┘ │
│                  │                           │
│  ┌───────────────▼─────────────────────────┐ │
│  │           Business Logic Layer          │ │
│  │  Auth · Balance · Transaction Services  │ │
│  └───────────────┬─────────────────────────┘ │
│                  │                           │
│  ┌───────────────▼─────────────────────────┐ │
│  │          Data Access Layer              │ │
│  │  SQLite queries via Python sqlite3/ORM  │ │
│  └───────────────┬─────────────────────────┘ │
└──────────────────┼───────────────────────────┘
                   │  SQL Queries
                   ▼
┌──────────────────────────────────────────────┐
│            DATABASE  (SQLite)                │
│                                              │
│   customers table · transactions table       │
└──────────────────────────────────────────────┘
```

### Frontend → Backend → Database Interaction

1. The browser renders static HTML pages (Jinja2 templates served by Flask).
2. Forms submit HTTP requests (POST) to Flask route handlers.
3. Flask validates input, enforces session authentication, and calls the business logic layer.
4. The business logic layer queries SQLite and returns results.
5. Flask renders the appropriate template with the result data and sends the HTTP response.

### Request Lifecycle

```
Browser                Flask Route          Business Logic         SQLite
   │                       │                      │                   │
   │── POST /login ────────►│                      │                   │
   │                        │── validate creds ───►│                   │
   │                        │                      │── SELECT user ───►│
   │                        │                      │◄─ user row ───────│
   │                        │◄─ auth result ───────│                   │
   │                        │── set session ─┐     │                   │
   │◄── 302 /dashboard ─────│               │      │                   │
   │                        │               │      │                   │
   │── GET /dashboard ──────►│               │      │                   │
   │                        │── get balance ──────►│                   │
   │                        │                      │── SELECT balance ►│
   │                        │◄─────────────────────│── balance row ────│
   │◄── 200 dashboard.html ─│                      │                   │
```

---

## 3. Component Design

### Frontend Responsibilities

| Responsibility | Detail |
|---|---|
| **Page Rendering** | Display Login, Dashboard, Deposit, and Withdraw pages using Bootstrap-styled HTML |
| **Form Handling** | Collect and submit user credentials and transaction amounts via HTML forms |
| **User Feedback** | Show success/error flash messages returned by the backend |
| **Navigation** | Provide links between dashboard, deposit, withdraw, and logout |
| **Responsiveness** | Use Bootstrap grid and utility classes to support mobile and desktop viewports |

The frontend holds **no business logic** and performs **no direct database access**. All state lives on the server.

### Backend Responsibilities

| Responsibility | Detail |
|---|---|
| **Routing** | Map URL endpoints to handler functions |
| **Authentication** | Verify credentials, create and destroy server-side sessions |
| **Authorisation** | Protect routes behind a login-required guard |
| **Business Logic** | Apply deposit/withdrawal rules (positive amounts, sufficient funds) |
| **Template Rendering** | Render Jinja2 HTML templates with context data |
| **Database Access** | Execute parameterised SQL queries against the SQLite file |
| **Error Handling** | Return user-friendly error messages for invalid inputs or failed operations |

### Database Responsibilities

| Responsibility | Detail |
|---|---|
| **Customer Storage** | Persist customer credentials (username + hashed password) and account metadata |
| **Balance Persistence** | Maintain the current account balance per customer |
| **Transaction Log** | Record each deposit and withdrawal with amount and timestamp |
| **Data Integrity** | Enforce constraints (e.g., non-negative balance) at the data layer |

---

## 4. Folder Structure

```
Banking-application-Bob-demo/
│
├── FRONTEND/                        # All client-side assets
│   └── templates/                   # Jinja2 HTML templates (served by Flask)
│       ├── login.html               # Login form page
│       ├── dashboard.html           # Account overview / balance display
│       ├── deposit.html             # Deposit funds form
│       └── withdraw.html            # Withdraw funds form
│
├── BACKEND/                         # All server-side code
│   ├── app.py                       # Flask application entry point; route definitions
│   ├── auth.py                      # Authentication helpers (password hashing, session logic)
│   ├── transactions.py              # Deposit and withdrawal business logic
│   ├── database.py                  # Database connection and query helpers
│   ├── seed.py                      # One-time script to create tables and seed demo customer
│   ├── banking.db                   # SQLite database file (auto-created)
│   └── requirements.txt             # Python dependencies (Flask, Werkzeug)
│
├── tests/                           # Automated test suite
│   └── test_app.py                  # Pytest test cases for routes and business logic
│
├── .github/
│   └── workflows/
│       └── banking-app-ci.yml       # GitHub Actions CI pipeline
│
└── IMPLEMENTATION_PLAN.md           # This document
```

### Folder Responsibility Summary

| Folder / File | Responsibility |
|---|---|
| `FRONTEND/templates/` | All user-facing HTML pages; no logic, only presentation |
| `BACKEND/app.py` | Application factory, route registration, request/response handling |
| `BACKEND/auth.py` | Login validation, password hashing, session creation and teardown |
| `BACKEND/transactions.py` | Deposit/withdrawal rules and balance update logic |
| `BACKEND/database.py` | SQLite connection management and reusable query functions |
| `BACKEND/seed.py` | Database initialisation and demo data seeding |
| `BACKEND/banking.db` | Persistent SQLite data file |
| `tests/` | Isolated unit and integration tests; no production dependency |

---

## 5. Module Breakdown

### Authentication Module

**Covers:** `BACKEND/auth.py`, `/login` and `/logout` routes in `app.py`, `FRONTEND/templates/login.html`

| Concern | Approach |
|---|---|
| Credential verification | Compare submitted password against stored hash using Werkzeug's `check_password_hash` |
| Password storage | Store passwords with `generate_password_hash` (never plain text) |
| Session creation | Store `customer_id` in Flask's signed session cookie on successful login |
| Session teardown | Clear session data on logout and redirect to login page |
| Route protection | A `login_required` decorator redirects unauthenticated requests to `/login` |

---

### Dashboard Module

**Covers:** `/dashboard` route in `app.py`, `FRONTEND/templates/dashboard.html`

| Concern | Approach |
|---|---|
| Balance retrieval | Query the current balance for the logged-in `customer_id` from the database |
| Account summary | Display customer name and current balance on the dashboard page |
| Navigation | Provide links to Deposit, Withdraw, and Logout actions |
| Flash messages | Display one-time success/error messages from previous operations |

---

### Account Management Module

**Covers:** `BACKEND/database.py`, `BACKEND/seed.py`

| Concern | Approach |
|---|---|
| Customer record | Store and retrieve customer profile and balance data |
| Database initialisation | `seed.py` creates tables and inserts one demo customer on first run |
| Connection handling | `database.py` provides a context-managed SQLite connection used by all modules |

---

### Transactions Module

**Covers:** `BACKEND/transactions.py`, `/deposit` and `/withdraw` routes in `app.py`, deposit/withdraw templates

| Concern | Approach |
|---|---|
| Deposit | Accept a positive amount, add to balance, log transaction record |
| Withdrawal | Accept a positive amount, verify sufficient funds, deduct from balance, log transaction record |
| Validation | Reject zero or negative amounts and overdraft attempts before writing to the database |
| Feedback | Return success or error message to be rendered via Flask flash on the dashboard |

---

## 6. Implementation Roadmap

### Development Phases

| Phase | Description | Key Deliverables | Depends On |
|---|---|---|---|
| **Phase 1 — Foundation** | Set up project structure, Flask app skeleton, and database layer | Folder tree, `app.py` skeleton, `database.py`, `seed.py`, `banking.db` created | Nothing |
| **Phase 2 — Authentication** | Implement login/logout flow with session management | Working `/login` and `/logout` routes, `login.html`, `auth.py`, `login_required` decorator | Phase 1 |
| **Phase 3 — Dashboard** | Build the authenticated dashboard with balance display | Working `/dashboard` route, `dashboard.html` rendering customer balance | Phase 2 |
| **Phase 4 — Transactions** | Implement deposit and withdrawal features | Working `/deposit` and `/withdraw` routes, form pages, balance updates | Phase 3 |
| **Phase 5 — Polish & Testing** | Improve UI feedback, add input validation, write pytest tests | Flash messages, error states, `tests/test_app.py` passing in CI | Phase 4 |

### Estimated Effort

| Phase | Relative Effort |
|---|---|
| Phase 1 — Foundation | Low |
| Phase 2 — Authentication | Medium |
| Phase 3 — Dashboard | Low |
| Phase 4 — Transactions | Medium |
| Phase 5 — Polish & Testing | Medium |

### Dependencies

```
Phase 1 (Foundation)
    └── Phase 2 (Authentication)
            └── Phase 3 (Dashboard)
                    └── Phase 4 (Transactions)
                                └── Phase 5 (Polish & Testing)
```

- **External:** Python 3.11+, Flask, Werkzeug must be available in the development environment.
- **Bootstrap CDN** must be reachable from the browser (or templates updated to use a local copy).
- **GitHub Actions CI** (`banking-app-ci.yml`) depends on the `tests/` directory and `requirements.txt` existing before the pipeline is triggered.

---

*End of Implementation Plan — Planning level only. No schema, SQL, API contracts, or implementation code is included in this document.*
