"""
test_app.py — Unit and Integration Tests for the Banking Application

Coverage:
  Unit tests     : auth.verify_login, transactions.deposit, transactions.withdraw
  Integration    : All Flask routes — happy paths and validation failures
  Database       : Each test suite gets a fresh in-memory SQLite database so
                   tests are fully isolated from each other and from banking.db.

Run with:
    pytest tests/test_app.py -v
"""

import sys
import os
import sqlite3
import pytest

# ---------------------------------------------------------------------------
# Path setup — allow imports from BACKEND/ when running from project root
# ---------------------------------------------------------------------------

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "BACKEND")
sys.path.insert(0, BACKEND_DIR)

# ---------------------------------------------------------------------------
# In-memory database fixture
# ---------------------------------------------------------------------------

TEST_DB_PATH = ":memory:"

# We monkeypatch the DB_PATH constant in `database` so all database.py
# functions operate against a fresh in-memory database during testing.

import database as db_module
from werkzeug.security import generate_password_hash


def _create_test_db():
    """Return an in-memory connection with the schema and one test customer."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE customers (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL UNIQUE,
            password TEXT    NOT NULL,
            name     TEXT    NOT NULL,
            balance  REAL    NOT NULL DEFAULT 0.0
                CHECK (balance >= 0)
        );
        CREATE TABLE transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            type        TEXT    NOT NULL CHECK (type IN ('deposit', 'withdrawal')),
            amount      REAL    NOT NULL CHECK (amount > 0),
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.execute(
        "INSERT INTO customers (username, password, name, balance) VALUES (?, ?, ?, ?)",
        ("test_user", generate_password_hash("TestPass1!"), "Test User", 500.00),
    )
    conn.commit()
    return conn


@pytest.fixture(autouse=True)
def patch_db(monkeypatch, tmp_path):
    """Redirect every database.py function to a fresh temp SQLite file."""
    db_file = str(tmp_path / "test_banking.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_file)
    db_module.init_db()
    # Seed a test customer
    hashed_pw = generate_password_hash("TestPass1!")
    db_module.insert_customer("test_user", hashed_pw, "Test User", 500.00)
    yield


# ---------------------------------------------------------------------------
# Flask app test client fixture
# ---------------------------------------------------------------------------

import app as flask_app_module


@pytest.fixture()
def client():
    flask_app_module.app.config["TESTING"] = True
    flask_app_module.app.config["WTF_CSRF_ENABLED"] = False
    flask_app_module.app.secret_key = "test-secret"
    with flask_app_module.app.test_client() as c:
        yield c


# ============================================================================
# UNIT TESTS — auth.verify_login
# ============================================================================

from auth import verify_login, create_session, destroy_session


class TestVerifyLogin:
    def test_success_with_valid_credentials(self):
        result = verify_login("test_user", "TestPass1!")
        assert result["success"] is True
        assert result["customer"]["username"] == "test_user"
        assert result["error"] is None

    def test_failure_wrong_password(self):
        result = verify_login("test_user", "WrongPass!")
        assert result["success"] is False
        assert "Invalid" in result["error"]
        assert result["customer"] is None

    def test_failure_unknown_username(self):
        result = verify_login("nobody", "AnyPass1!")
        assert result["success"] is False
        assert "Invalid" in result["error"]
        assert result["customer"] is None

    def test_failure_empty_username(self):
        result = verify_login("", "TestPass1!")
        assert result["success"] is False
        assert result["error"] is not None

    def test_failure_empty_password(self):
        result = verify_login("test_user", "")
        assert result["success"] is False
        assert result["error"] is not None

    def test_generic_error_does_not_reveal_username_existence(self):
        """Wrong password and unknown username must return the same message."""
        r1 = verify_login("test_user", "BadPass!")
        r2 = verify_login("nobody_here", "BadPass!")
        assert r1["error"] == r2["error"]


# ============================================================================
# UNIT TESTS — transactions.deposit
# ============================================================================

from transactions import deposit, withdraw
from database import get_balance, get_customer_by_username


def _get_test_customer_id():
    customer = get_customer_by_username("test_user")
    return customer["id"]


class TestDeposit:
    def test_valid_deposit_increases_balance(self):
        cid = _get_test_customer_id()
        result = deposit(cid, "200.00")
        assert result["success"] is True
        assert result["new_balance"] == pytest.approx(700.00)

    def test_deposit_zero_is_rejected(self):
        cid = _get_test_customer_id()
        result = deposit(cid, "0")
        assert result["success"] is False
        assert "greater than zero" in result["error"]

    def test_deposit_negative_is_rejected(self):
        cid = _get_test_customer_id()
        result = deposit(cid, "-50")
        assert result["success"] is False
        assert "greater than zero" in result["error"]

    def test_deposit_non_numeric_is_rejected(self):
        cid = _get_test_customer_id()
        result = deposit(cid, "abc")
        assert result["success"] is False
        assert "valid number" in result["error"]

    def test_deposit_empty_string_is_rejected(self):
        cid = _get_test_customer_id()
        result = deposit(cid, "")
        assert result["success"] is False

    def test_deposit_does_not_write_on_validation_failure(self):
        cid = _get_test_customer_id()
        before = get_balance(cid)
        deposit(cid, "-10")
        after = get_balance(cid)
        assert before == after


# ============================================================================
# UNIT TESTS — transactions.withdraw
# ============================================================================

class TestWithdraw:
    def test_valid_withdrawal_decreases_balance(self):
        cid = _get_test_customer_id()
        result = withdraw(cid, "100.00")
        assert result["success"] is True
        assert result["new_balance"] == pytest.approx(400.00)

    def test_withdrawal_exceeding_balance_is_rejected(self):
        cid = _get_test_customer_id()
        result = withdraw(cid, "600.00")
        assert result["success"] is False
        assert "Insufficient" in result["error"]

    def test_withdrawal_zero_is_rejected(self):
        cid = _get_test_customer_id()
        result = withdraw(cid, "0")
        assert result["success"] is False

    def test_withdrawal_negative_is_rejected(self):
        cid = _get_test_customer_id()
        result = withdraw(cid, "-20")
        assert result["success"] is False

    def test_withdrawal_non_numeric_is_rejected(self):
        cid = _get_test_customer_id()
        result = withdraw(cid, "xyz")
        assert result["success"] is False
        assert "valid number" in result["error"]

    def test_withdrawal_does_not_write_on_validation_failure(self):
        cid = _get_test_customer_id()
        before = get_balance(cid)
        withdraw(cid, "9999999")
        after = get_balance(cid)
        assert before == after

    def test_withdrawal_exact_balance_succeeds(self):
        """Withdrawing exactly the available balance should work."""
        cid = _get_test_customer_id()
        result = withdraw(cid, "500.00")
        assert result["success"] is True
        assert result["new_balance"] == pytest.approx(0.00)


# ============================================================================
# INTEGRATION TESTS — Flask routes via test client
# ============================================================================

class TestLoginRoute:
    def test_get_login_returns_200(self, client):
        r = client.get("/login")
        assert r.status_code == 200

    def test_root_redirects_to_login(self, client):
        r = client.get("/")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_login_with_valid_credentials_redirects_to_dashboard(self, client):
        r = client.post("/login", data={"username": "test_user", "password": "TestPass1!"}, follow_redirects=False)
        assert r.status_code == 302
        assert "/dashboard" in r.headers["Location"]

    def test_login_with_invalid_credentials_returns_login_page(self, client):
        r = client.post("/login", data={"username": "test_user", "password": "WrongPass"}, follow_redirects=True)
        assert r.status_code == 200
        assert b"Invalid" in r.data

    def test_login_sets_session_on_success(self, client):
        with client.session_transaction() as sess:
            assert "customer_id" not in sess
        client.post("/login", data={"username": "test_user", "password": "TestPass1!"})
        with client.session_transaction() as sess:
            assert "customer_id" in sess


class TestProtectedRoutes:
    def test_dashboard_redirects_when_not_logged_in(self, client):
        r = client.get("/dashboard")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_deposit_redirects_when_not_logged_in(self, client):
        r = client.get("/deposit")
        assert r.status_code == 302

    def test_withdraw_redirects_when_not_logged_in(self, client):
        r = client.get("/withdraw")
        assert r.status_code == 302

    def _login(self, client):
        client.post("/login", data={"username": "test_user", "password": "TestPass1!"})

    def test_dashboard_returns_200_when_logged_in(self, client):
        self._login(client)
        r = client.get("/dashboard")
        assert r.status_code == 200
        assert b"500.00" in r.data

    def test_deposit_get_returns_200_when_logged_in(self, client):
        self._login(client)
        r = client.get("/deposit")
        assert r.status_code == 200

    def test_withdraw_get_returns_200_when_logged_in(self, client):
        self._login(client)
        r = client.get("/withdraw")
        assert r.status_code == 200


class TestDepositRoute:
    def _login(self, client):
        client.post("/login", data={"username": "test_user", "password": "TestPass1!"})

    def test_valid_deposit_redirects_to_dashboard(self, client):
        self._login(client)
        r = client.post("/deposit", data={"amount": "200"}, follow_redirects=False)
        assert r.status_code == 302
        assert "/dashboard" in r.headers["Location"]

    def test_valid_deposit_increases_balance_on_dashboard(self, client):
        self._login(client)
        client.post("/deposit", data={"amount": "200"})
        r = client.get("/dashboard")
        assert b"700.00" in r.data

    def test_zero_deposit_shows_error(self, client):
        self._login(client)
        r = client.post("/deposit", data={"amount": "0"}, follow_redirects=True)
        assert r.status_code == 200
        assert b"greater than zero" in r.data

    def test_non_numeric_deposit_shows_error(self, client):
        self._login(client)
        r = client.post("/deposit", data={"amount": "abc"}, follow_redirects=True)
        assert r.status_code == 200
        assert b"valid number" in r.data


class TestWithdrawRoute:
    def _login(self, client):
        client.post("/login", data={"username": "test_user", "password": "TestPass1!"})

    def test_valid_withdrawal_redirects_to_dashboard(self, client):
        self._login(client)
        r = client.post("/withdraw", data={"amount": "100"}, follow_redirects=False)
        assert r.status_code == 302
        assert "/dashboard" in r.headers["Location"]

    def test_valid_withdrawal_decreases_balance_on_dashboard(self, client):
        self._login(client)
        client.post("/withdraw", data={"amount": "100"})
        r = client.get("/dashboard")
        assert b"400.00" in r.data

    def test_insufficient_funds_shows_error(self, client):
        self._login(client)
        r = client.post("/withdraw", data={"amount": "9999"}, follow_redirects=True)
        assert r.status_code == 200
        assert b"Insufficient" in r.data

    def test_zero_withdrawal_shows_error(self, client):
        self._login(client)
        r = client.post("/withdraw", data={"amount": "0"}, follow_redirects=True)
        assert r.status_code == 200
        assert b"greater than zero" in r.data


class TestLogoutRoute:
    def test_logout_clears_session(self, client):
        client.post("/login", data={"username": "test_user", "password": "TestPass1!"})
        with client.session_transaction() as sess:
            assert "customer_id" in sess
        client.get("/logout")
        with client.session_transaction() as sess:
            assert "customer_id" not in sess

    def test_logout_redirects_to_login(self, client):
        client.post("/login", data={"username": "test_user", "password": "TestPass1!"})
        r = client.get("/logout", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_logout_when_not_logged_in_redirects_cleanly(self, client):
        r = client.get("/logout", follow_redirects=False)
        assert r.status_code == 302


class TestErrorHandlers:
    def test_404_returns_custom_page(self, client):
        r = client.get("/this-page-does-not-exist")
        assert r.status_code == 404
        assert b"404" in r.data
