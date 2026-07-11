"""
auth.py — Authentication Module

Responsibilities:
  - verify_login(username, password)  →  validates credentials against DB
  - login_required                    →  route decorator for protected pages
  - create_session(customer_id)       →  writes customer_id into Flask session
  - destroy_session()                 →  clears all session data on logout
"""

from functools import wraps

from flask import session, redirect, url_for, flash
from werkzeug.security import check_password_hash

from database import get_customer_by_username


# ---------------------------------------------------------------------------
# Credential verification
# ---------------------------------------------------------------------------

def verify_login(username, password):
    """Check submitted credentials against the stored hash.

    Returns a dict: {'success': bool, 'customer': row_dict_or_None, 'error': str_or_None}

    A single generic error message is returned for both "username not found"
    and "wrong password" to prevent account enumeration (NFR-04).
    """
    # Guard: empty fields are rejected before any DB hit.
    if not username or not password:
        return {"success": False, "customer": None, "error": "Please enter both username and password."}

    customer = get_customer_by_username(username)

    # Guard: unknown username — same message as wrong password.
    if customer is None:
        return {"success": False, "customer": None, "error": "Invalid username or password."}

    # Guard: password hash mismatch.
    if not check_password_hash(customer["password"], password):
        return {"success": False, "customer": None, "error": "Invalid username or password."}

    return {"success": True, "customer": customer, "error": None}


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def create_session(customer_id, customer_name):
    """Store the authenticated customer's identity in the signed session cookie."""
    session["customer_id"] = customer_id
    session["customer_name"] = customer_name


def destroy_session():
    """Remove all session data, effectively logging the customer out."""
    session.clear()


# ---------------------------------------------------------------------------
# Route protection decorator
# ---------------------------------------------------------------------------

def login_required(f):
    """Decorator that redirects unauthenticated requests to /login.

    Usage:
        @app.route('/dashboard')
        @login_required
        def dashboard():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "customer_id" not in session:
            flash("Please log in to access that page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function
