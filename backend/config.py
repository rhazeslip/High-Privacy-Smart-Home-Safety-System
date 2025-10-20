# backend/config.py
# Centralized configuration and thresholds for alerts.

from pydantic import BaseModel
from typing import Optional

class Settings(BaseModel):
    project_name: str = "HP-SHSS Edge Hub"
    debug: bool = True
    #Thresholds aligning with SRS (can be tuned later)
    gas_ppm_threshold: float = 70.0          # CO example
    co_ppm_threshold: float = 70.0
    smoke_threshold: float = 0.6             # arbitrary normalized unit
    temp_rise_threshold_c: float = 12.0      # rapid rise in °C within short window
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

def get_settings() -> Settings:
    #Could be extended to load from .env in the future.
    return Settings()
