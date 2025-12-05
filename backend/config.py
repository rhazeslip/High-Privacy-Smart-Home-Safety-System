# backend/config.py
# Centralized configuration and thresholds for alerts.

from pydantic import BaseModel
from typing import Optional
import os

def _get_bool_env(key: str, default: bool) -> bool:
    """Get boolean from environment variable."""
    val = os.getenv(key)
    if val is None:
        return default
    return val.lower() in ('true', '1', 'yes', 'on')

def _get_int_env(key: str, default: int) -> int:
    """Get integer from environment variable."""
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default

class Settings(BaseModel):
    project_name: str = "HP-SHSS Edge Hub"
    debug: bool = _get_bool_env('HP_SHSS_DEBUG', True)
    
    # Thresholds aligning with SRS (can be tuned later)
    gas_ppm_threshold: float = 70.0          # CO example
    co_ppm_threshold: float = 70.0
    smoke_threshold: float = 0.6             # arbitrary normalized unit
    temp_rise_threshold_c: float = 12.0      # rapid rise in °C within short window
    cors_origins: list[str] = ["https://localhost:3000", "https://127.0.0.1:3000"]
    
    # Rate limiting
    rate_limit_window: int = _get_int_env('HP_SHSS_RATE_LIMIT_WINDOW', 60)
    max_login_attempts: int = _get_int_env('HP_SHSS_MAX_LOGIN_ATTEMPTS', 5)
    max_salt_requests: int = _get_int_env('HP_SHSS_MAX_SALT_REQUESTS', 10)
    max_reset_attempts: int = _get_int_env('HP_SHSS_MAX_RESET_ATTEMPTS', 3)
    
    # Database
    db_wal_mode: bool = _get_bool_env('HP_SHSS_DB_WAL_MODE', True)
    
    # Logging
    log_level: str = os.getenv('HP_SHSS_LOG_LEVEL', 'INFO')
    audit_log: bool = _get_bool_env('HP_SHSS_AUDIT_LOG', True)
    
    # Backup
    backup_dir: str = os.getenv('HP_SHSS_BACKUP_DIR', 'backups')
    backup_keep: int = _get_int_env('HP_SHSS_BACKUP_KEEP', 7)

# Singleton settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get settings instance (cached singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
