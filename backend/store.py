# backend/store.py
# Simple in-memory store for sensors and alerts (MVP).

from typing import Dict, List, Optional
from .models import Alert, SensorReading
import sqlite3
import os
from datetime import datetime
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
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            hashed_pw TEXT,
            role TEXT,
            salt TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            token TEXT PRIMARY KEY,
            username TEXT,
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
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    _DB.commit()

    # If running under pytest, ensure a clean DB state for deterministic tests.
    try:
        import sys
        if 'pytest' in sys.modules:
            cur.execute("DELETE FROM alerts")
            cur.execute("DELETE FROM sensors")
            cur.execute("DELETE FROM refresh_tokens")
            cur.execute("DELETE FROM settings")
            cur.execute("DELETE FROM users")
            _DB.commit()
    except Exception:
        pass

    # Don't seed demo users anymore - they will be created during setup wizard
    # This comment preserves the structure but removes auto-seeding


_init_db()

def save_reading(reading: SensorReading) -> None:
    # keep in-memory for quick access/tests
    SENSOR_LAST[reading.sensor_id] = reading
    # persist into sqlite
    cur = _DB.cursor()
    cur.execute(
        "REPLACE INTO sensors(sensor_id, type, value, location, ts) VALUES (?, ?, ?, ?, ?)",
        (reading.sensor_id, reading.type, json.dumps(reading.value), reading.location, reading.ts.isoformat()),
    )
    _DB.commit()

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
    # Return a shallow copy so callers don't mutate the module-level dict directly.
    # overlay DB-backed settings if present
    cur = _DB.cursor()
    cur.execute("SELECT key, value FROM settings")
    rows = cur.fetchall()
    out = dict(HOME_SETTINGS)
    for r in rows:
        try:
            out[r['key']] = json.loads(r['value'])
        except Exception:
            out[r['key']] = r['value']
    return out


### User persistence helpers
def db_get_user(username: str) -> Optional[dict]:
    cur = _DB.cursor()
    cur.execute("SELECT username, hashed_pw, role, salt FROM users WHERE username = ?", (username,))
    r = cur.fetchone()
    if not r:
        return None
    return {"username": r['username'], "hashed_pw": r['hashed_pw'], "role": r['role'], "salt": r['salt']}


def db_create_user(username: str, hashed_pw: str, role: str = "Occupant") -> bool:
    try:
        cur = _DB.cursor()
        cur.execute("INSERT INTO users(username, hashed_pw, role) VALUES (?, ?, ?)", (username, hashed_pw, role))
        _DB.commit()
        return True
    except Exception:
        return False


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
    # Only allow updating known keys to avoid accidental pollution.
    allowed = {"armed", "mode", "notify_email"}
    for k, v in new.items():
        if k in allowed:
            HOME_SETTINGS[k] = v
            # persist
            cur = _DB.cursor()
            cur.execute("REPLACE INTO settings(key, value) VALUES (?, ?)", (k, json.dumps(v)))
    _DB.commit()
    return get_home_settings()


### Refresh token helpers (persisted)
def save_refresh_token(token: str, username: str, expires_at: datetime) -> None:
    cur = _DB.cursor()
    cur.execute("REPLACE INTO refresh_tokens(token, username, expires_at) VALUES (?, ?, ?)", (token, username, expires_at.isoformat()))
    _DB.commit()

def get_refresh_token(token: str) -> Optional[dict]:
    cur = _DB.cursor()
    cur.execute("SELECT token, username, expires_at FROM refresh_tokens WHERE token = ?", (token,))
    r = cur.fetchone()
    if not r:
        return None
    return {"token": r['token'], "username": r['username'], "expires_at": r['expires_at']}

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
    cur = _DB.cursor()
    cur.execute("SELECT value FROM system_config WHERE key = ?", ('setup_complete',))
    r = cur.fetchone()
    return r and r['value'] == 'true'

def mark_setup_complete() -> None:
    """Mark initial setup as complete"""
    cur = _DB.cursor()
    cur.execute("REPLACE INTO system_config(key, value) VALUES (?, ?)", ('setup_complete', 'true'))
    _DB.commit()

def get_system_config(key: str) -> Optional[str]:
    """Get a system configuration value"""
    cur = _DB.cursor()
    cur.execute("SELECT value FROM system_config WHERE key = ?", (key,))
    r = cur.fetchone()
    return r['value'] if r else None

def set_system_config(key: str, value: str) -> None:
    """Set a system configuration value"""
    cur = _DB.cursor()
    cur.execute("REPLACE INTO system_config(key, value) VALUES (?, ?)", (key, value))
    _DB.commit()

def get_home_name() -> str:
    """Get the configured home name"""
    return get_system_config('home_name') or 'My Home'

def set_home_name(name: str) -> None:
    """Set the home name"""
    set_system_config('home_name', name)

def get_recovery_key() -> Optional[str]:
    """Get the admin recovery key"""
    return get_system_config('recovery_key')

def set_recovery_key(key: str) -> None:
    """Set the admin recovery key"""
    set_system_config('recovery_key', key)
