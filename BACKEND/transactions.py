"""
transactions.py — Transaction Service Layer

Responsibilities:
  - deposit(customer_id, amount_str)   →  validates and applies a deposit
  - withdraw(customer_id, amount_str)  →  validates and applies a withdrawal

Both functions accept the raw string from the HTML form so that all
type-conversion and validation happen here before touching the database.
They return a dict: {'success': bool, 'error': str_or_None}
"""

from database import get_balance, apply_deposit, apply_withdrawal

# Maximum single-transaction amount (simple safeguard).
MAX_TRANSACTION = 100_000.00


# ---------------------------------------------------------------------------
# Shared validation helper
# ---------------------------------------------------------------------------

def _parse_amount(amount_str):
    """Convert the form string to a positive float, or raise ValueError."""
    try:
        value = float(amount_str)
    except (TypeError, ValueError):
        raise ValueError("Amount must be a valid number.")

    if value <= 0:
        raise ValueError("Amount must be greater than zero.")

    if value > MAX_TRANSACTION:
        raise ValueError(f"Amount exceeds the maximum allowed per transaction (${MAX_TRANSACTION:,.2f}).")

    return round(value, 2)


# ---------------------------------------------------------------------------
# Deposit
# ---------------------------------------------------------------------------

def deposit(customer_id, amount_str):
    """Validate and apply a deposit to the customer's account.

    Steps:
      1. Parse and validate the amount string.
      2. Fetch current balance (confirms the customer record exists).
      3. Delegate the double-write (balance update + transaction log) to the
         data access layer inside a single DB transaction.
      4. Return success result with the new balance.
    """
    try:
        amount = _parse_amount(amount_str)
    except ValueError as exc:
        return {"success": False, "error": str(exc)}

    current_balance = get_balance(customer_id)
    if current_balance is None:
        return {"success": False, "error": "Account not found."}

    apply_deposit(customer_id, amount)
    new_balance = get_balance(customer_id)

    return {
        "success": True,
        "error": None,
        "amount": amount,
        "new_balance": new_balance,
    }


# ---------------------------------------------------------------------------
# Withdrawal
# ---------------------------------------------------------------------------

def withdraw(customer_id, amount_str):
    """Validate and apply a withdrawal from the customer's account.

    Steps:
      1. Parse and validate the amount string.
      2. Fetch current balance.
      3. Check that balance >= amount (insufficient-funds guard).
      4. Delegate the double-write to the data access layer.
      5. Return success result with the new balance.
    """
    try:
        amount = _parse_amount(amount_str)
    except ValueError as exc:
        return {"success": False, "error": str(exc)}

    current_balance = get_balance(customer_id)
    if current_balance is None:
        return {"success": False, "error": "Account not found."}

    if amount > current_balance:
        return {
            "success": False,
            "error": (
                f"Insufficient funds. Your current balance is ${current_balance:,.2f}."
            ),
        }

    apply_withdrawal(customer_id, amount)
    new_balance = get_balance(customer_id)

    return {
        "success": True,
        "error": None,
        "amount": amount,
        "new_balance": new_balance,
    }
