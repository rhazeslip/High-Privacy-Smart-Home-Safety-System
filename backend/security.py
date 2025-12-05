# Password hashing and JWT utility helpers.

from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
import os
import secrets

# Read secret from environment for production. If not provided, generate a
# reasonably strong random secret for local/dev runs. In production, set
# HP_SHSS_JWT_SECRET to a long, random value and keep it secret.
JWT_SECRET = os.getenv('HP_SHSS_JWT_SECRET') or secrets.token_urlsafe(64)
JWT_ALG = "HS256"
# Shorter access token lifetime for better security (refresh tokens can be
# added later). 15 minutes is a sensible default for access tokens.
ACCESS_TOKEN_EXPIRE_MIN = int(os.getenv('HP_SHSS_ACCESS_EXPIRE_MIN', '15'))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    # Hash plain password using bcrypt.
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    # Verify plain password against hashed password.
    return pwd_context.verify(plain, hashed)

def create_access_token(expires_minutes: Optional[int] = None) -> str:
    """Create a signed JWT for the single admin user."""
    expire_min = expires_minutes if expires_minutes is not None else ACCESS_TOKEN_EXPIRE_MIN
    expire = datetime.utcnow() + timedelta(minutes=expire_min)
    # include a jti to allow future revocation lists
    payload = {"sub": "admin", "exp": expire, "jti": secrets.token_urlsafe(8)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str) -> dict:
    # Decode JWT and return claims (raises on invalid/expired).
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])


def create_refresh_token(days: int = 7) -> tuple[str, datetime]:
    """Create a random refresh token for admin, return (token, expires_at) and persist it.

    Uses the backend.store persistence layer so refresh tokens survive restarts.
    """
    import secrets as _secrets
    from datetime import datetime as _dt, timedelta as _td
    # import store lazily to avoid circular imports at module load time
    from . import store as _store

    token = _secrets.token_urlsafe(32)
    expires_at = _dt.utcnow() + _td(days=days)
    _store.save_refresh_token(token, expires_at)
    return token, expires_at


def verify_refresh_token(token: str) -> bool:
    """Verify refresh token exists and not expired. Returns True if valid."""
    from datetime import datetime as _dt
    from . import store as _store

    rec = _store.get_refresh_token(token)
    if not rec:
        return False
    try:
        expires = _dt.fromisoformat(rec['expires_at'])
    except Exception:
        return False
    if _dt.utcnow() > expires:
        # expired — remove record
        _store.revoke_refresh_token(token)
        return False
    return True


def hash_recovery_key(recovery_key: str) -> str:
    """Hash a recovery key for secure storage using SHA-256."""
    import hashlib
    return hashlib.sha256(recovery_key.encode()).hexdigest()


def verify_recovery_key(provided_key: str, stored_hash: str) -> bool:
    """Securely compare recovery key against stored hash."""
    import hmac
    import hashlib
    provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
    return hmac.compare_digest(provided_hash, stored_hash)
