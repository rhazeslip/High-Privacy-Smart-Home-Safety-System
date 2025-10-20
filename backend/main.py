# backend/main.py
# FastAPI app for HP-SHSS Edge Hub

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from .models import SensorReading, Alert, StatusResponse
from .store import save_reading, list_alerts, acknowledge_alert, count_open_alerts, SENSOR_LAST
from .logic import process_reading
from .config import get_settings

S = get_settings()
app = FastAPI(title=S.project_name, debug=S.debug)

# Allow requests from local React dev server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=S.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status", response_model=StatusResponse)
def status():
    # Basic health/status endpoint for the client.
    return StatusResponse(
        system="running",
        sensors_online=len(SENSOR_LAST),
        alerts_open=count_open_alerts()
    )

@app.post("/sensor", response_model=dict)
def ingest_sensor(reading: SensorReading):
    # Ingest a sensor reading, save last reading, and run alert logic.
    save_reading(reading)
    alerts = process_reading(reading)
    return {
        "ok": True,
        "alerts_created": len(alerts),
        "alert_ids": [str(a.id) for a in alerts]
    }

@app.get("/alerts", response_model=List[Alert])
def get_alerts(include_ack: bool = False):
    # List current (or all) alerts for the dashboard.
    return list_alerts(include_ack=include_ack)

@app.post("/alerts/{alert_id}/ack", response_model=dict)
def ack_alert(alert_id: str):
    # Allow clients to acknowledge an alert.
    if not acknowledge_alert(alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"ok": True, "acknowledged": alert_id}
