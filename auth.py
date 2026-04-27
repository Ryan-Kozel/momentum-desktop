"""Authentication helpers — PBKDF2 password hashing (upgrade from plain SHA-256)."""
from __future__ import annotations

import hashlib
import os

import database as db

ITERATIONS = 200_000


def _hash(password: str, salt: bytes) -> str:
    """PBKDF2-HMAC-SHA256."""
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return dk.hex()


def register(username: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    if not username:
        return False, "Username cannot be empty."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."
    if db.get_user_by_username(username):
        return False, "Username already exists."

    salt = os.urandom(16)
    pw_hash = _hash(password, salt)
    db.create_user(username, pw_hash, salt.hex())
    return True, "Registered successfully."


def login(username: str, password: str) -> tuple[bool, str, int | None]:
    user = db.get_user_by_username(username.strip())
    if not user:
        return False, "Invalid username or password.", None
    salt = bytes.fromhex(user["salt"])
    if _hash(password, salt) != user["password_hash"]:
        return False, "Invalid username or password.", None
    return True, "Welcome back.", user["id"]
