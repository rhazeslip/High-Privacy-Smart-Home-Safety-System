# Simple in-memory user store with roles (Admin/Occupant).

from typing import Optional, Dict
from .security import hash_password, verify_password

# Demo users (username -> {hashed_pw, role})
_USERS: Dict[str, dict] = {
    "admin":   {"hashed_pw": hash_password("admin123"),   "role": "Admin"},
    "alice":   {"hashed_pw": hash_password("alice123"),   "role": "Occupant"},
}

def get_user(username: str) -> Optional[dict]:
    # Return user record by username.
    return _USERS.get(username)

def check_credentials(username: str, password: str) -> Optional[str]:
    # Validate credentials; return role if ok.
    user = get_user(username)
    if not user: 
        return None
    if verify_password(password, user["hashed_pw"]):
        return user["role"]
    return None

def create_user(username: str, password: str, role: str = "Occupant") -> bool:
    # Create new user if not exists.
    if username in _USERS:
        return False
    _USERS[username] = {"hashed_pw": hash_password(password), "role": role}
    return True
