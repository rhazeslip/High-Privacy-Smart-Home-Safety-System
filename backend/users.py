"""Single admin user helpers.

This module provides simplified authentication for the single admin user.
The system only supports one admin user created during initial setup.
"""

from typing import Optional
from .security import verify_password
from . import store


def get_admin() -> Optional[dict]:
    """Return admin user record or None.

    The returned dict has keys: 'hashed_pw', 'salt'.
    """
    return store.db_get_admin()


def verify_admin_password(client_hash: str) -> bool:
    """Validate admin password hash.

    Returns True if valid, False otherwise.
    """
    admin = get_admin()
    if not admin:
        return False
    if client_hash is None:
        return False
    return verify_password(client_hash, admin["hashed_pw"])
