# backend/models.py
# Pydantic models for sensor readings, alerts, and basic responses.

from pydantic import BaseModel, Field
from typing import Optional, Literal, Union
from datetime import datetime
from uuid import UUID, uuid4

SensorType = Literal["door","window","garage","gas","co","water","fire","smoke","temp"]

class SensorReading(BaseModel):
    sensor_id: str = Field(..., description="Unique sensor id")
    type: SensorType
    #'value' meaning:
    # - entry sensors: value as 'open' or 'closed'
    # - gas/co: numeric ppm
    # - water: 0/1 or boolean-like numeric
    # - smoke: 0.0~1.0 normalized
    # - temp: °C
    value: Union[float, str]
    location: Optional[str] = "Unknown"
    ts: datetime = Field(default_factory=datetime.utcnow)

class Alert(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    level: Literal["info","warning","critical"]
    title: str
    message: str
    sensor_id: str
    location: str = "Unknown"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False

class StatusResponse(BaseModel):
    system: str = "running"
    sensors_online: int = 0
    alerts_open: int = 0

# Auth-related models for login/token (single admin user).

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    # Single admin user - username not needed
    # Either provide `password` (legacy) or `client_hash` (PBKDF2 hex) derived with server salt.
    password: Optional[str] = None
    client_hash: Optional[str] = None

class UserInfo(BaseModel):
    """Simplified user info - single admin user only."""
    authenticated: bool = True


# Setup wizard models
class SetupStatus(BaseModel):
    setup_complete: bool
    home_name: Optional[str] = None

class SetupRequest(BaseModel):
    home_name: str
    admin_password: str
    confirm_password: str

class SetupResponse(BaseModel):
    success: bool
    recovery_key: str
    message: str

class PasswordResetRequest(BaseModel):
    recovery_key: str
    new_password: str
    confirm_password: str

class PasswordResetResponse(BaseModel):
    success: bool
    message: str

class ChangePasswordRequest(BaseModel):
    current_password_hash: str
    new_password: str