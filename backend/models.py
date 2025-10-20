# backend/models.py
# Pydantic models for sensor readings, alerts, and basic responses.

from pydantic import BaseModel, Field
from typing import Optional, Literal, Union
from typing import Optional, Literal
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
