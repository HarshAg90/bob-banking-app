"""
seed.py — Database initialisation and demo data seeding.

Run this script once before the first application start:
    python BACKEND/seed.py

Subsequent runs are safe — the script checks for the demo customer before
inserting and will not create duplicate records.
"""

import sys
import os

# Allow running directly from the project root as well as from BACKEND/.
sys.path.insert(0, os.path.dirname(__file__))

from werkzeug.security import generate_password_hash
from database import init_db, customer_exists, insert_customer

DEMO_USERNAME = "demo_user"
DEMO_PASSWORD = "SecurePass123!"
DEMO_NAME = "Alex Johnson"
DEMO_BALANCE = 1000.00


def seed():
    # 1. Ensure tables exist.
    init_db()
    print("[seed] Tables created / verified.")

    # 2. Insert demo customer only if not already present.
    if customer_exists(DEMO_USERNAME):
        print(f"[seed] Demo customer '{DEMO_USERNAME}' already exists — skipping insert.")
        return

    hashed_pw = generate_password_hash(DEMO_PASSWORD)
    insert_customer(DEMO_USERNAME, hashed_pw, DEMO_NAME, DEMO_BALANCE)
    print(f"[seed] Demo customer created.")
    print(f"       Username : {DEMO_USERNAME}")
    print(f"       Password : {DEMO_PASSWORD}")
    print(f"       Balance  : ${DEMO_BALANCE:,.2f}")


if __name__ == "__main__":
    seed()
