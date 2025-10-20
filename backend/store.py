# backend/store.py
# Simple in-memory store for sensors and alerts (MVP).

from typing import Dict, List
from .models import Alert, SensorReading

SENSOR_LAST: Dict[str, SensorReading] = {}
ALERTS: List[Alert] = []

def save_reading(reading: SensorReading) -> None:
    SENSOR_LAST[reading.sensor_id] = reading

def add_alert(alert: Alert) -> Alert:
    ALERTS.append(alert)
    return alert

def list_alerts(include_ack: bool = False) -> List[Alert]:
    if include_ack:
        return list(ALERTS)
    return [a for a in ALERTS if not a.acknowledged]

def acknowledge_alert(alert_id) -> bool:
    for a in ALERTS:
        if str(a.id) == str(alert_id):
            a.acknowledged = True
            return True
    return False

def count_open_alerts() -> int:
    return sum(1 for a in ALERTS if not a.acknowledged)
