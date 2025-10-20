# backend/logic.py
# Alert decision logic based on SRS thresholds.

from .models import SensorReading, Alert
from .store import add_alert
from .config import get_settings

S = get_settings()

def process_reading(reading: SensorReading) -> list[Alert]:
    alerts: list[Alert] = []

    t = reading.type
    v = reading.value
    loc = reading.location or "Unknown"

    # Entry points: door/window/garage
    if t in ("door","window","garage"):
        # Expect 'open'/'closed' as string value.
        if isinstance(v, str) and v.lower() == "open":
            alerts.append(add_alert(Alert(
                level="warning",
                title="Entry Open",
                message=f"{t.capitalize()} opened while armed? Check immediately.",
                sensor_id=reading.sensor_id,
                location=loc
            )))

    # Gas / CO in ppm
    elif t in ("gas","co"):
        try:
            ppm = float(v)
        except Exception:
            ppm = 0.0
        threshold = S.co_ppm_threshold if t == "co" else S.gas_ppm_threshold
        if ppm >= threshold:
            alerts.append(add_alert(Alert(
                level="critical",
                title=f"{t.upper()} Leak Detected",
                message=f"{t.upper()} = {ppm:.0f} ppm exceeds safe threshold.",
                sensor_id=reading.sensor_id,
                location=loc
            )))

    # Water leak: any positive value considered presence of water
    elif t == "water":
        try:
            water_present = float(v) > 0.0
        except Exception:
            water_present = False
        if water_present:
            alerts.append(add_alert(Alert(
                level="warning",
                title="Water Leak",
                message="Water detected at sensor location.",
                sensor_id=reading.sensor_id,
                location=loc
            )))

    # Smoke (0~1) and temperature rapid rise would need temporal context.
    # For MVP, trigger on smoke intensity alone.
    elif t == "smoke":
        try:
            s = float(v)
        except Exception:
            s = 0.0
        if s >= S.smoke_threshold:
            alerts.append(add_alert(Alert(
                level="critical",
                title="FIRE DETECTED",
                message="High smoke density detected. EVACUATE and CALL 911.",
                sensor_id=reading.sensor_id,
                location=loc
            )))

    # Temp: MVP does not implement rate-of-rise; can extend later.
    # elif t == "temp": ...

    return alerts
