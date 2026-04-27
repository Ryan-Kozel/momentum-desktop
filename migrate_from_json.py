"""One-time migration: import users.json + *_data.json from the old Flask app.

Usage:
    python migrate_from_json.py /path/to/old/project
    python migrate_from_json.py                     # (default: current dir)

The script:
  * reads users.json (username -> sha256(password) legacy hashes)
  * reads <username>_data.json for each user (both in CWD and data/)
  * migrates into momentum.db

Legacy SHA-256 passwords cannot be verified by the new PBKDF2 flow. On first
login after migration, the user can reset by re-registering. To make login
work immediately, this script also creates a placeholder PBKDF2 hash for each
user using "changeme" — CHANGE YOUR PASSWORD ON FIRST LOGIN.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import auth
import database as db


PLACEHOLDER_PASSWORD = "changeme"


def find_data_file(root: Path, username: str) -> Path | None:
    candidates = [
        root / f"{username}_data.json",
        root / "data" / f"{username}_data.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def migrate(root: Path) -> None:
    users_file = root / "users.json"
    if not users_file.exists():
        print(f"❌ No users.json found at {users_file}")
        return

    db.init_db()

    with users_file.open() as f:
        users = json.load(f)

    print(f"Found {len(users)} user(s) in users.json\n")

    for username in users:
        existing = db.get_user_by_username(username)
        if existing:
            print(f"  ↷ {username}: already exists in DB, skipping user row")
            user_id = existing["id"]
        else:
            # Create with placeholder password
            ok, msg = auth.register(username, PLACEHOLDER_PASSWORD)
            if not ok:
                print(f"  ✗ {username}: {msg}")
                continue
            user_id = db.get_user_by_username(username)["id"]
            print(f"  ✓ {username}: created (password = '{PLACEHOLDER_PASSWORD}')")

        data_file = find_data_file(root, username)
        if not data_file:
            print(f"    (no data file found for {username})")
            continue

        with data_file.open() as f:
            data = json.load(f)

        _import_logs_and_checklists(user_id, data.get("logs", {}))
        _import_activities(user_id, data.get("activities", {}))
        print(f"    → imported data from {data_file.name}")

    print("\nDone. Login with password 'changeme' and change it afterwards.")


def _import_logs_and_checklists(user_id: int, logs: dict) -> None:
    # The old format stored checklist as bool fields inside each log entry.
    LEGACY_CHECKLIST_MAP = {
        "made_bed": "Make Bed",
        "coded": "Code",
        "read": "Read",
        "move_body": "Move Body",
        "brush_teeth_2x": "Brush Teeth 2x",
    }

    # Build lookup {name -> id} for this user's checklist items
    items = db.get_checklist_items(user_id)
    name_to_id = {i["name"]: i["id"] for i in items}

    for d_str, log in logs.items():
        weight = log.get("weight")
        calories = log.get("calories")
        miles = log.get("miles")
        jobs = log.get("jobs")
        db.upsert_log(user_id, d_str, weight, calories, miles, jobs)

        for legacy_key, display_name in LEGACY_CHECKLIST_MAP.items():
            if legacy_key in log:
                iid = name_to_id.get(display_name)
                if iid is not None:
                    db.set_checklist_entry(user_id, iid, d_str, bool(log[legacy_key]))


def _import_activities(user_id: int, activities: dict) -> None:
    for d_str, acts in activities.items():
        for a in acts:
            db.add_activity(user_id, d_str, a)


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    migrate(path)
