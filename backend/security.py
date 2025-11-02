# Password hashing and JWT utility helpers.

from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext

# For demo purposes only; replace secret in production.
JWT_SECRET = "CHANGE_ME_TO_RANDOM_LONG_SECRET"
JWT_ALG = "HS256"
ACCESS_TOKEN_EXPIRE_MIN = 60  # 60 minutes

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    # Hash plain password using bcrypt.
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    # Verify plain password against hashed password.
    return pwd_context.verify(plain, hashed)

def create_access_token(sub: str, role: str) -> str:
    # Create a signed JWT with subject (username) and role.
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MIN)
    payload = {"sub": sub, "role": role, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str) -> dict:
    # Decode JWT and return claims (raises on invalid/expired).
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
