"""DB-backed user helpers.

This module delegates persistence to `backend.store` (SQLite). It keeps the
same function names/signatures used elsewhere in the codebase so existing
callers (tests and auth routes) continue to work.
"""

from typing import Optional
from .security import hash_password, verify_password
from . import store


def get_user(username: str) -> Optional[dict]:
    """Return user record by username or None.

    The returned dict has keys: 'username', 'hashed_pw', 'role'.
    """
    return store.db_get_user(username)


def check_credentials(username: str, password: str) -> Optional[str]:
    """Validate credentials; return role if ok.

    Returns None on failure.
    """
    user = get_user(username)
    if not user:
        return None
    if password is None:
        # No password provided — do not authenticate.
        return None
    if verify_password(password, user["hashed_pw"]):
        return user["role"]
    return None


def create_user(username: str, password: str, role: str = "Occupant") -> bool:
    """Create new user if not exists. Password is hashed before storing."""
    if store.db_get_user(username):
        return False
    hashed = hash_password(password)
    return store.db_create_user(username, hashed, role)
