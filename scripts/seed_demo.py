#!/usr/bin/env python3
"""
Demo initialization script.
Creates a default household for testing.

Run from repository root: python scripts/seed_demo.py
"""
import sys
import os

# Ensure repo root is on path when run as scripts/seed_demo.py
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from neuroion.core.memory.db import init_db, db_session
from neuroion.core.memory.repository import HouseholdRepository


def init_demo():
    """Initialize demo data."""
    # Initialize database
    init_db()

    # Create default household in a dedicated session
    with db_session() as db:
        # Check if household already exists
        households = HouseholdRepository.get_all(db)
        if households:
            print(f"✅ Demo household already exists with ID: {households[0].id}")
            return households[0].id

        household = HouseholdRepository.create(db, name="Demo Household")
        print(f"✅ Created demo household with ID: {household.id}")
        print(f"   Use this ID for pairing: {household.id}")
        return household.id


if __name__ == "__main__":
    household_id = init_demo()
    print(f"\n🎉 Demo initialized! Household ID: {household_id}")
    print(f"\nNext steps:")
    print(f"1. Start the server: python -m neuroion.core.main")
    print(f"2. Use household_id={household_id} for pairing")
