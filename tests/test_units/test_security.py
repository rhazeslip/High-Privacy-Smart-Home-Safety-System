import pytest
from backend.security import hash_password, verify_password, create_access_token, decode_token

class TestSecurity:
    def test_password_hashing(self):
        plain_password = "testpassword123"
        hashed = hash_password(plain_password)

        assert verify_password(plain_password, hashed)
        assert not verify_password("wrongpassword", hashed)
        assert hashed != plain_password

    def test_jwt_token_creation(self):
        username = "testuser"
        role = "Admin"

        token = create_access_token(username, role)
        decoded = decode_token(token)
        assert decoded["sub"] == username
        assert decoded["role"] == role
        assert "exp" in decoded
