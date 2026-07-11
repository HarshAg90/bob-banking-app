"""
database.py — Data Access Layer
Owns all SQLite interaction: connection management, table creation, and
every named query function. No other module contains raw SQL.
"""

import os
import sqlite3

# Absolute path to the database file so it works regardless of the
# directory from which Flask is launched.
DB_PATH = os.path.join(os.path.dirname(__file__), "banking.db")


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def get_connection():
    """Open and return a connection to the SQLite database.

    Rows are returned as sqlite3.Row objects, which support column access
    by name (row['balance']) as well as by index.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enforce foreign-key constraints and enable WAL for better concurrency.
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db():
    """Create tables if they do not already exist.

    Safe to call on every application startup — uses IF NOT EXISTS so
    existing data is never overwritten.
    """
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    NOT NULL UNIQUE,
                password TEXT    NOT NULL,
                name     TEXT    NOT NULL,
                balance  REAL    NOT NULL DEFAULT 0.0
                    CHECK (balance >= 0)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL
                    REFERENCES customers(id),
                type        TEXT    NOT NULL CHECK (type IN ('deposit', 'withdrawal')),
                amount      REAL    NOT NULL CHECK (amount > 0),
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );
        """)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Customer queries
# ---------------------------------------------------------------------------

def get_customer_by_username(username):
    """Return a single customer row by username, or None if not found."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM customers WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_customer_by_id(customer_id):
    """Return a single customer row by primary key, or None if not found."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_balance(customer_id):
    """Return the current balance (float) for the given customer."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT balance FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        return row["balance"] if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Transaction writes
# ---------------------------------------------------------------------------

def apply_deposit(customer_id, amount):
    """Add *amount* to the customer's balance and log the transaction.

    Both writes run inside a single transaction so the database is never
    left in a half-updated state.
    """
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE customers SET balance = balance + ? WHERE id = ?",
            (amount, customer_id),
        )
        conn.execute(
            "INSERT INTO transactions (customer_id, type, amount) VALUES (?, 'deposit', ?)",
            (customer_id, amount),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def apply_withdrawal(customer_id, amount):
    """Subtract *amount* from the customer's balance and log the transaction.

    Both writes run inside a single transaction.  The CHECK constraint on
    the customers table (balance >= 0) provides a final safety net at the
    database level, but the service layer validates first.
    """
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE customers SET balance = balance - ? WHERE id = ?",
            (amount, customer_id),
        )
        conn.execute(
            "INSERT INTO transactions (customer_id, type, amount) VALUES (?, 'withdrawal', ?)",
            (customer_id, amount),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Seed helper (used by seed.py and tests)
# ---------------------------------------------------------------------------

def customer_exists(username):
    """Return True if a customer with the given username already exists."""
    return get_customer_by_username(username) is not None


def insert_customer(username, hashed_password, name, balance):
    """Insert a new customer record. Raises IntegrityError on duplicate username."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO customers (username, password, name, balance) VALUES (?, ?, ?, ?)",
            (username, hashed_password, name, balance),
        )
        conn.commit()
    finally:
        conn.close()
