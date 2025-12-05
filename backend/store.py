# backend/store.py
# Simple in-memory store for sensors and alerts (MVP).

from typing import Dict, List, Optional
from .models import Alert, SensorReading
import sqlite3
import os
from datetime import datetime, timedelta
import json

# Keep in-memory view for tests and simple usage, but persist to sqlite for
# better durability. This preserves the existing module-level symbols used by
# tests (`ALERTS`, `SENSOR_LAST`) while providing persistence.
SENSOR_LAST: Dict[str, SensorReading] = {}
ALERTS: List[Alert] = []

# SQLite DB path under backend/ so repository is self-contained for dev.
DB_PATH = os.path.join(os.path.dirname(__file__), 'data.db')
_DB = sqlite3.connect(DB_PATH, check_same_thread=False)
_DB.row_factory = sqlite3.Row


def _init_db():
    cur = _DB.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            level TEXT,
            title TEXT,
            message TEXT,
            sensor_id TEXT,
            location TEXT,
            created_at TEXT,
            acknowledged INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sensors (
            sensor_id TEXT PRIMARY KEY,
            type TEXT,
            value TEXT,
            location TEXT,
            ts TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sensor_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT NOT NULL,
            type TEXT NOT NULL,
            value TEXT NOT NULL,
            location TEXT,
            ts TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT,
            category TEXT DEFAULT 'system'
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            token TEXT PRIMARY KEY,
            expires_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            location TEXT,
            port INTEGER,
            paired INTEGER DEFAULT 0,
            shared_secret TEXT,
            model TEXT,
            firmware_version TEXT,
            added_at TEXT,
            last_seen TEXT,
            battery INTEGER DEFAULT 100
        )
        """
    )
    
    # Create indexes for better query performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_sensor ON alerts(sensor_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sensor_history_sensor ON sensor_history(sensor_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sensor_history_ts ON sensor_history(ts DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_config_category ON config(category)")
    
    # Migrate data from old tables if they exist
    _migrate_legacy_tables(cur)
    
    _DB.commit()

    # If running under pytest, ensure a clean DB state for deterministic tests.
    try:
        import sys
        if 'pytest' in sys.modules:
            cur.execute("DELETE FROM alerts")
            cur.execute("DELETE FROM sensors")
            cur.execute("DELETE FROM sensor_history")
            cur.execute("DELETE FROM refresh_tokens")
            cur.execute("DELETE FROM config")
            _DB.commit()
    except Exception:
        pass


def _migrate_legacy_tables(cur):
    """Migrate data from legacy settings and system_config tables to unified config table."""
    try:
        # Check if old settings table exists and has data
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        if cur.fetchone():
            cur.execute("SELECT key, value FROM settings")
            for row in cur.fetchall():
                cur.execute(
                    "INSERT OR IGNORE INTO config(key, value, category) VALUES (?, ?, 'user')",
                    (row['key'], row['value'])
                )
            # Drop the old table after migration
            cur.execute("DROP TABLE IF EXISTS settings")
    except Exception:
        pass
    
    try:
        # Check if old system_config table exists and has data
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_config'")
        if cur.fetchone():
            cur.execute("SELECT key, value FROM system_config")
            for row in cur.fetchall():
                # Security-related keys go to 'security' category
                category = 'security' if 'password' in row['key'] or 'salt' in row['key'] or 'recovery' in row['key'] else 'system'
                cur.execute(
                    "INSERT OR IGNORE INTO config(key, value, category) VALUES (?, ?, ?)",
                    (row['key'], row['value'], category)
                )
            # Drop the old table after migration
            cur.execute("DROP TABLE IF EXISTS system_config")
    except Exception:
        pass


_init_db()

def save_reading(reading: SensorReading, save_history: bool = True) -> None:
    """Save a sensor reading. Updates the current state and optionally stores in history."""
    # keep in-memory for quick access/tests
    SENSOR_LAST[reading.sensor_id] = reading
    # persist current state into sqlite
    cur = _DB.cursor()
    cur.execute(
        "REPLACE INTO sensors(sensor_id, type, value, location, ts) VALUES (?, ?, ?, ?, ?)",
        (reading.sensor_id, reading.type, json.dumps(reading.value), reading.location, reading.ts.isoformat()),
    )
    # Also store in history for analytics/trends
    if save_history:
        cur.execute(
            "INSERT INTO sensor_history(sensor_id, type, value, location, ts) VALUES (?, ?, ?, ?, ?)",
            (reading.sensor_id, reading.type, json.dumps(reading.value), reading.location, reading.ts.isoformat()),
        )
    _DB.commit()


def get_sensor_history(sensor_id: str = None, limit: int = 100, since: str = None) -> List[dict]:
    """Get sensor reading history for analytics.
    
    Args:
        sensor_id: Optional sensor ID to filter by
        limit: Maximum number of records to return
        since: Optional ISO datetime string to filter readings after this time
    
    Returns:
        List of sensor reading dictionaries ordered by timestamp descending
    """
    cur = _DB.cursor()
    q = "SELECT sensor_id, type, value, location, ts FROM sensor_history"
    conds = []
    params: List[object] = []
    
    if sensor_id:
        conds.append("sensor_id = ?")
        params.append(sensor_id)
    if since:
        conds.append("ts >= ?")
        params.append(since)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)
    
    cur.execute(q, params)
    rows = cur.fetchall()
    
    result = []
    for r in rows:
        try:
            result.append({
                "sensor_id": r['sensor_id'],
                "type": r['type'],
                "value": json.loads(r['value']),
                "location": r['location'],
                "ts": r['ts']
            })
        except Exception:
            continue
    return result


def cleanup_sensor_history(days_to_keep: int = 30) -> int:
    """Remove sensor history older than specified days.
    
    Args:
        days_to_keep: Number of days of history to retain
    
    Returns:
        Number of records deleted
    """
    cur = _DB.cursor()
    cutoff = (datetime.utcnow() - timedelta(days=days_to_keep)).isoformat()
    cur.execute("DELETE FROM sensor_history WHERE ts < ?", (cutoff,))
    deleted = cur.rowcount
    _DB.commit()
    return deleted


def add_alert(alert: Alert) -> Alert:
    ALERTS.append(alert)
    cur = _DB.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO alerts(id, level, title, message, sensor_id, location, created_at, acknowledged) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (str(alert.id), alert.level, alert.title, alert.message, alert.sensor_id, alert.location, alert.created_at.isoformat(), int(alert.acknowledged)),
    )
    _DB.commit()
    return alert

def list_alerts(include_ack: bool = False) -> List[Alert]:
    if include_ack:
        return list(ALERTS)
    return [a for a in ALERTS if not a.acknowledged]

def acknowledge_alert(alert_id) -> bool:
    for a in ALERTS:
        if str(a.id) == str(alert_id):
            a.acknowledged = True
            cur = _DB.cursor()
            cur.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (str(alert_id),))
            _DB.commit()
            return True
    return False

def count_open_alerts() -> int:
    return sum(1 for a in ALERTS if not a.acknowledged)


# Simple in-memory home settings for the frontend to read/update.
# Keep this minimal and non-persistent (MVP only).
HOME_SETTINGS = {
    "armed": False,
    "mode": "home",  # other modes: away, night
    "notify_email": "",
}

def get_home_settings() -> dict:
    """Return home settings, overlaying DB-backed user settings."""
    cur = _DB.cursor()
    cur.execute("SELECT key, value FROM config WHERE category = 'user'")
    rows = cur.fetchall()
    out = dict(HOME_SETTINGS)
    for r in rows:
        try:
            out[r['key']] = json.loads(r['value'])
        except Exception:
            out[r['key']] = r['value']
    return out


### Admin credential helpers (single admin user)
def db_get_admin() -> Optional[dict]:
    """Get admin credentials from config table."""
    hashed_pw = get_config('admin_hashed_pw', 'security')
    salt = get_config('admin_salt', 'security')
    if not hashed_pw:
        return None
    return {"hashed_pw": hashed_pw, "salt": salt}


def db_set_admin_password(hashed_pw: str, salt: str) -> None:
    """Set admin password in config table."""
    set_config('admin_hashed_pw', hashed_pw, 'security')
    set_config('admin_salt', salt, 'security')


def get_all_alerts_from_db(include_ack: bool = True, limit: int = 100, since: Optional[str] = None) -> List[Alert]:
    """Return alerts from the DB as a list of Alert models.

    - include_ack: whether to include acknowledged alerts
    - limit: max number of rows to return (ordered by created_at desc)
    - since: optional ISO datetime string to filter alerts created after this time
    """
    cur = _DB.cursor()
    q = "SELECT id, level, title, message, sensor_id, location, created_at, acknowledged FROM alerts"
    conds = []
    params: List[object] = []
    if not include_ack:
        conds.append("acknowledged = 0")
    if since:
        conds.append("created_at >= ?")
        params.append(since)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    cur.execute(q, params)
    rows = cur.fetchall()
    out: List[Alert] = []
    for r in rows:
        try:
            a = Alert(
                id=r['id'],
                level=r['level'],
                title=r['title'],
                message=r['message'],
                sensor_id=r['sensor_id'],
                location=r['location'],
                created_at=datetime.fromisoformat(r['created_at']),
                acknowledged=bool(r['acknowledged'])
            )
            out.append(a)
        except Exception:
            # skip malformed rows
            continue
    return out


def db_get_alert(alert_id: str) -> Optional[Alert]:
    cur = _DB.cursor()
    cur.execute("SELECT id, level, title, message, sensor_id, location, created_at, acknowledged FROM alerts WHERE id = ?", (str(alert_id),))
    r = cur.fetchone()
    if not r:
        return None
    try:
        return Alert(
            id=r['id'],
            level=r['level'],
            title=r['title'],
            message=r['message'],
            sensor_id=r['sensor_id'],
            location=r['location'],
            created_at=datetime.fromisoformat(r['created_at']),
            acknowledged=bool(r['acknowledged'])
        )
    except Exception:
        return None

def update_home_settings(new: dict) -> dict:
    """Update home settings. Only allows updating known keys."""
    allowed = {"armed", "mode", "notify_email"}
    cur = _DB.cursor()
    for k, v in new.items():
        if k in allowed:
            HOME_SETTINGS[k] = v
            # persist to unified config table with 'user' category
            cur.execute(
                "REPLACE INTO config(key, value, category) VALUES (?, ?, 'user')",
                (k, json.dumps(v))
            )
    _DB.commit()
    return get_home_settings()


### Refresh token helpers (persisted) - single admin user, no username needed
def save_refresh_token(token: str, expires_at: datetime) -> None:
    cur = _DB.cursor()
    cur.execute("REPLACE INTO refresh_tokens(token, expires_at) VALUES (?, ?)", (token, expires_at.isoformat()))
    _DB.commit()

def get_refresh_token(token: str) -> Optional[dict]:
    cur = _DB.cursor()
    cur.execute("SELECT token, expires_at FROM refresh_tokens WHERE token = ?", (token,))
    r = cur.fetchone()
    if not r:
        return None
    return {"token": r['token'], "expires_at": r['expires_at']}

def revoke_refresh_token(token: str) -> None:
    cur = _DB.cursor()
    cur.execute("DELETE FROM refresh_tokens WHERE token = ?", (token,))
    _DB.commit()


### Device management helpers
def save_device(device_id: str, name: str, device_type: str, location: str, port: int, 
                paired: bool = False, shared_secret: str = None, 
                model: str = "HP-SHSS-SIM", firmware_version: str = "1.0.0") -> None:
    """Save or update a device in the database"""
    cur = _DB.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        """INSERT OR REPLACE INTO devices 
           (device_id, name, type, location, port, paired, shared_secret, model, firmware_version, added_at, last_seen)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT added_at FROM devices WHERE device_id = ?), ?), ?)""",
        (device_id, name, device_type, location, port, int(paired), shared_secret, 
         model, firmware_version, device_id, now, now)
    )
    _DB.commit()

def get_device(device_id: str) -> Optional[dict]:
    """Get a device by ID"""
    cur = _DB.cursor()
    cur.execute(
        "SELECT device_id, name, type, location, port, paired, shared_secret, model, firmware_version, added_at, last_seen FROM devices WHERE device_id = ?",
        (device_id,)
    )
    r = cur.fetchone()
    if not r:
        return None
    return {
        "device_id": r['device_id'],
        "name": r['name'],
        "type": r['type'],
        "location": r['location'],
        "port": r['port'],
        "paired": bool(r['paired']),
        "shared_secret": r['shared_secret'],
        "model": r['model'],
        "firmware_version": r['firmware_version'],
        "added_at": r['added_at'],
        "last_seen": r['last_seen']
    }

def get_all_devices() -> List[dict]:
    """Get all registered devices"""
    cur = _DB.cursor()
    cur.execute(
        "SELECT device_id, name, type, location, port, paired, shared_secret, model, firmware_version, added_at, last_seen FROM devices ORDER BY added_at DESC"
    )
    rows = cur.fetchall()
    devices = []
    for r in rows:
        devices.append({
            "device_id": r['device_id'],
            "name": r['name'],
            "type": r['type'],
            "location": r['location'],
            "port": r['port'],
            "paired": bool(r['paired']),
            "shared_secret": r['shared_secret'],
            "model": r['model'],
            "firmware_version": r['firmware_version'],
            "added_at": r['added_at'],
            "last_seen": r['last_seen']
        })
    return devices

def update_device_last_seen(device_id: str) -> None:
    """Update the last seen timestamp for a device"""
    cur = _DB.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("UPDATE devices SET last_seen = ? WHERE device_id = ?", (now, device_id))
    _DB.commit()

def delete_device(device_id: str) -> bool:
    """Delete a device from the database"""
    cur = _DB.cursor()
    cur.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
    _DB.commit()
    return cur.rowcount > 0


### First-time setup helpers
def is_setup_complete() -> bool:
    """Check if initial setup has been completed"""
    return get_config('setup_complete', 'system') == 'true'

def mark_setup_complete() -> None:
    """Mark initial setup as complete"""
    set_config('setup_complete', 'true', 'system')


### Unified config table accessors
def get_config(key: str, category: str = 'system') -> Optional[str]:
    """Get a configuration value from the unified config table.
    
    Args:
        key: The configuration key
        category: The category ('system', 'user', or 'security')
    
    Returns:
        The configuration value or None if not found
    """
    cur = _DB.cursor()
    cur.execute("SELECT value FROM config WHERE key = ? AND category = ?", (key, category))
    r = cur.fetchone()
    return r['value'] if r else None

def set_config(key: str, value: str, category: str = 'system') -> None:
    """Set a configuration value in the unified config table.
    
    Args:
        key: The configuration key
        value: The value to store
        category: The category ('system', 'user', or 'security')
    """
    cur = _DB.cursor()
    cur.execute(
        "REPLACE INTO config(key, value, category) VALUES (?, ?, ?)",
        (key, value, category)
    )
    _DB.commit()


# Legacy aliases for backward compatibility
def get_system_config(key: str) -> Optional[str]:
    """Legacy: Get a system configuration value. Use get_config() instead."""
    return get_config(key, 'system')

def set_system_config(key: str, value: str) -> None:
    """Legacy: Set a system configuration value. Use set_config() instead."""
    set_config(key, value, 'system')


def get_home_name() -> str:
    """Get the configured home name"""
    return get_config('home_name', 'system') or 'My Home'

def set_home_name(name: str) -> None:
    """Set the home name"""
    set_config('home_name', name, 'system')

def get_recovery_key() -> Optional[str]:
    """Get the admin recovery key (hashed)"""
    return get_config('recovery_key', 'security')

def set_recovery_key(key: str) -> None:
    """Set the admin recovery key (should be hashed before storing)"""
    set_config('recovery_key', key, 'security')
