# backend/main.py
# FastAPI app for HP-SHSS Edge Hub

from fastapi import FastAPI, HTTPException, Depends, Header
from typing import List, Optional
from .models import SensorReading, Alert, StatusResponse, LoginRequest, Token, UserInfo
from .store import save_reading, list_alerts, acknowledge_alert, count_open_alerts, SENSOR_LAST
from .logic import process_reading
from .config import get_settings
from .security import create_access_token, decode_token
from .users import check_credentials, get_user

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


# Auth helpers
def get_current_user(authorization: Optional[str] = Header(None)) -> UserInfo:
    # EN: Parse "Authorization: Bearer <token>" and validate.
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        claims = decode_token(token)
        username = claims.get("sub")
        role = claims.get("role")
        if not username or not role:
            raise ValueError("Bad token claims")
        return UserInfo(username=username, role=role)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def require_admin(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    # EN: Only allow Admin role for certain endpoints.
    if user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


# Auth routes
@app.post("/auth/login", response_model=Token)
def login(req: LoginRequest):
    # Validate credentials and return a JWT access token.
    role = check_credentials(req.username, req.password)
    if not role:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(sub=req.username, role=role)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/auth/me", response_model=UserInfo)
def me(user: UserInfo = Depends(get_current_user)):
    # Return current user info from JWT.
    return user

# Protect sensitive actions
@app.post("/alerts/{alert_id}/ack", response_model=dict)
def ack_alert(alert_id: str, user: UserInfo = Depends(get_current_user)):
    # Require authentication to acknowledge alerts.
    if not acknowledge_alert(alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"ok": True, "acknowledged": alert_id, "by": user.username}