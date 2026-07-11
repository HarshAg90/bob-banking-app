"""
app.py — Flask Application Entry Point

Responsibilities:
  - Create and configure the Flask application instance.
  - Register all URL routes.
  - Register custom error handlers.
  - Call init_db() on startup so tables always exist before the first request.

Run with:
    flask --app BACKEND/app.py run
or (with .flaskenv configured):
    flask run
"""

import os
import sys

# Allow imports of sibling modules (database, auth, transactions) when Flask
# is launched from the project root directory.
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, request, redirect, url_for, flash, session

from database import init_db, get_customer_by_id, get_balance
from auth import verify_login, create_session, destroy_session, login_required
from transactions import deposit, withdraw

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

# Templates live in FRONTEND/templates/ (outside the BACKEND package), so we
# must supply an explicit path relative to this file.
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "FRONTEND", "templates")

app = Flask(__name__, template_folder=TEMPLATE_DIR)

# Secret key signs and verifies session cookies (NFR-01, NFR-02).
# In production, read this from an environment variable or secrets manager.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# Initialise the database (creates tables if absent) at application startup.
with app.app_context():
    init_db()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Root URL — redirect to login."""
    return redirect(url_for("login"))


# ── Authentication ──────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    GET  : Render login page. If already logged in, go to dashboard.
    POST : Validate credentials. On success, create session and redirect to
           dashboard. On failure, re-render login with a generic error.
    """
    # Already authenticated — skip the login page.
    if "customer_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        result = verify_login(username, password)

        if result["success"]:
            customer = result["customer"]
            create_session(customer["id"], customer["name"])
            flash(f"Welcome back, {customer['name']}!", "success")
            return redirect(url_for("dashboard"))

        flash(result["error"], "danger")
        return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clear the session and redirect to login."""
    destroy_session()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ── Dashboard ───────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    """
    Display the authenticated customer's name and current balance.
    Flash messages from previous operations are rendered here.
    """
    customer_id = session["customer_id"]
    customer = get_customer_by_id(customer_id)
    balance = get_balance(customer_id)

    return render_template(
        "dashboard.html",
        customer_name=customer["name"],
        balance=balance,
    )


# ── Deposit ─────────────────────────────────────────────────────────────────

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit_route():
    """
    GET  : Render the deposit form.
    POST : Call the deposit service. On success, flash confirmation and
           redirect to dashboard. On failure, re-render the form with error.
    """
    if request.method == "POST":
        amount_str = request.form.get("amount", "").strip()
        result = deposit(session["customer_id"], amount_str)

        if result["success"]:
            flash(
                f"Deposit of ${result['amount']:,.2f} successful. "
                f"New balance: ${result['new_balance']:,.2f}.",
                "success",
            )
            return redirect(url_for("dashboard"))

        flash(result["error"], "danger")
        return render_template("deposit.html")

    return render_template("deposit.html")


# ── Withdraw ─────────────────────────────────────────────────────────────────

@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw_route():
    """
    GET  : Render the withdraw form with the current balance shown.
    POST : Call the withdrawal service. On success, flash confirmation and
           redirect to dashboard. On failure, re-render the form with error.
    """
    customer_id = session["customer_id"]
    balance = get_balance(customer_id)

    if request.method == "POST":
        amount_str = request.form.get("amount", "").strip()

        # --- Validation checks (route-level, before any service call) ---
        if not amount_str:
            flash("Amount is required", "danger")
            return render_template("withdraw.html", balance=balance)

        try:
            amount_value = float(amount_str)
        except ValueError:
            amount_value = None

        if amount_value is None or amount_value <= 0:
            flash("Amount must be greater than zero", "danger")
            return render_template("withdraw.html", balance=balance)

        if amount_value > balance:
            flash("Insufficient funds", "danger")
            return render_template("withdraw.html", balance=balance)
        # --- End validation checks ---

        result = withdraw(customer_id, amount_str)

        if result["success"]:
            flash(
                f"Withdrawal of ${result['amount']:,.2f} successful. "
                f"New balance: ${result['new_balance']:,.2f}.",
                "success",
            )
            return redirect(url_for("dashboard"))

        flash(result["error"], "danger")
        return render_template("withdraw.html", balance=balance)

    return render_template("withdraw.html", balance=balance)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    app.logger.error("Server error: %s", e)
    return render_template("500.html"), 500


# ---------------------------------------------------------------------------
# Entry point (for direct `python app.py` execution)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)