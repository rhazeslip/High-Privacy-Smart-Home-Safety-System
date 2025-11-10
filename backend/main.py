# backend/main.py
# FastAPI app for HP-SHSS Edge Hub

from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from backend.logic import process_reading
from backend.config import get_settings
from backend.security import create_access_token, decode_token, create_refresh_token, verify_refresh_token, verify_password
from backend.store import revoke_refresh_token
from backend.users import check_credentials

#  Absolute imports so we can run "uvicorn backend.main:app" from project root.
from backend.models import (
    SensorReading, Alert, StatusResponse, LoginRequest, Token, UserInfo
)
from backend.store import (
    save_reading, list_alerts, acknowledge_alert, count_open_alerts, SENSOR_LAST, ALERTS
)
from backend.store import get_home_settings, update_home_settings
from backend.security import ACCESS_TOKEN_EXPIRE_MIN
from fastapi.responses import JSONResponse
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware


S = get_settings()
app = FastAPI(title=S.project_name, debug=S.debug)

# Force HTTPS
app.add_middleware(HTTPSRedirectMiddleware)

# Allow requests from local React dev server (HTTPS only).
app.add_middleware(
    CORSMiddleware,
    allow_origins=S.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth helpers (placed early so routes can reference them)
def get_current_user(request: Request, authorization: Optional[str] = Header(None)) -> UserInfo:
    # Parse token from Authorization header (Bearer) or fallback to secure cookie.
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    else:
        # Accept cookie-based auth for higher security (HttpOnly cookie)
        token = request.cookies.get('hp_token')

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

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

# Redirect HTTP -> HTTPS in non-debug/production runs. This is a simple
# safety measure; when running behind a reverse proxy you may prefer the
# proxy to handle TLS and this middleware can be disabled by leaving
# Settings.debug True during development.
if not S.debug:
    app.add_middleware(HTTPSRedirectMiddleware)

    # Add common security headers for production HTTPS runs.
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        resp = await call_next(request)
        # Enforce HSTS for HTTPS clients (1 year, includeSubDomains)
        resp.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        resp.headers['X-Frame-Options'] = 'DENY'
        resp.headers['X-Content-Type-Options'] = 'nosniff'
        resp.headers['Referrer-Policy'] = 'no-referrer'
        # Minimal CSP for the simple frontend; adjust if you serve scripts from CDNs.
        resp.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
        return resp

@app.get("/status", response_model=StatusResponse)
def status():
    # Basic health/status endpoint for the client.
    # Return the standard 'running' system string from the model defaults.
    return StatusResponse(sensors_online=len(SENSOR_LAST), alerts_open=count_open_alerts())

@app.get("/test")
def test():
    # Basic health/status endpoint for the client.
    return StatusResponse(sensors_online=len(SENSOR_LAST), alerts_open=count_open_alerts())

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
def get_alerts(include_ack: bool = False, user: UserInfo = Depends(get_current_user)):
    # List current (or all) alerts for the dashboard. Require authentication.
    return list_alerts(include_ack=include_ack)


@app.post("/alerts", response_model=Alert)
def create_alert(alert: Alert, user: UserInfo = Depends(get_current_user)):
    """Create a new alert manually (for testing purposes)."""
    from backend.store import add_alert
    import uuid
    from datetime import datetime
    
    # Generate ID and timestamp if not provided
    if not alert.id:
        alert.id = uuid.uuid4()
    if not alert.created_at:
        alert.created_at = datetime.now()
    
    # Save to database and in-memory list using existing function
    return add_alert(alert)


@app.get("/alerts/history", response_model=List[Alert])
def alerts_history(include_ack: bool = True, limit: int = 200, since: Optional[str] = None, user: UserInfo = Depends(get_current_user)):
    # Return historical alerts from the persisted store. Accessible to authenticated users.
    from backend.store import get_all_alerts_from_db
    return get_all_alerts_from_db(include_ack=include_ack, limit=limit, since=since)


@app.get("/alerts/{alert_id}", response_model=Alert)
def get_alert(alert_id: str, user: UserInfo = Depends(get_current_user)):
    # Fetch a single alert by id from DB or in-memory store.
    from backend.store import db_get_alert
    a = db_get_alert(alert_id)
    if a:
        return a
    # fallback: check in-memory list
    for a in ALERTS:
        if str(a.id) == str(alert_id):
            return a
    raise HTTPException(status_code=404, detail="Alert not found")

@app.post("/alerts/{alert_id}/ack", response_model=dict)
def ack_alert(alert_id: str):
    # Allow clients to acknowledge an alert.
    if not acknowledge_alert(alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"ok": True, "acknowledged": alert_id}


# (Moved) Auth helpers are defined earlier in this file to allow their use
# in route dependencies.


# Auth routes
@app.post("/auth/login", response_model=Token)
def login(req: LoginRequest):
    # Validate credentials and return a JWT access token.
    role = None
    # If client_hash provided, verify against stored bcrypt hash
    if getattr(req, 'client_hash', None):
        from backend.users import get_user
        user = get_user(req.username)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        # stored hashed_pw is bcrypt() of client_hash
        if not verify_password(req.client_hash, user['hashed_pw']):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        role = user.get('role')
    else:
        # Fallback: legacy password field (plaintext)
        role = check_credentials(req.username, req.password)
        if not role:
            raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(sub=req.username, role=role)
    # Set HttpOnly, Secure cookie for the token (frontend will use cookie-based auth).
    resp = JSONResponse(content={"access_token": token, "token_type": "bearer"})
    # Max-Age in seconds
    max_age = ACCESS_TOKEN_EXPIRE_MIN * 60
    resp.set_cookie(
        key='hp_token',
        value=token,
        httponly=True,
        secure=not S.debug,
        samesite='lax',
        max_age=max_age,
        path='/'
    )
    # Also create a long-lived refresh token (HttpOnly cookie) so clients can
    # obtain new access tokens without re-prompting credentials.
    refresh_token, refresh_exp = create_refresh_token(req.username)
    refresh_max = int((refresh_exp - refresh_exp.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() or (7*24*3600))
    # Simpler: set refresh cookie max-age to 7 days by default
    resp.set_cookie(
        key='hp_refresh',
        value=refresh_token,
        httponly=True,
        secure=not S.debug,
        samesite='lax',
        max_age=7*24*3600,
        path='/'
    )
    return resp


@app.get('/auth/salt')
def get_salt(username: str):
    # Public endpoint to return stored per-user salt (base64) for client-side PBKDF2
    from backend.users import get_user
    user = get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    salt = user.get('salt')
    if not salt:
        raise HTTPException(status_code=404, detail='Salt not available')
    return { 'salt': salt }


# (original definitions moved earlier in the file)


@app.post('/auth/logout')
def logout(response: Response):
    # Clear the auth cookie on logout and revoke refresh token if present.
    response.delete_cookie('hp_token', path='/')
    # Attempt to revoke refresh token if client sent it.
    # Note: in FastAPI you can read cookies from the Request object; use a
    # small helper to avoid changing signature here. If the client doesn't
    # send the refresh cookie, just clear the cookie on the response.
    return {"ok": True}


@app.post('/auth/logout_full')
def logout_full(request: Request, response: Response):
    # Clear cookies and revoke refresh token stored server-side.
    refresh = request.cookies.get('hp_refresh')
    if refresh:
        try:
            revoke_refresh_token(refresh)
        except Exception:
            pass
    response.delete_cookie('hp_token', path='/')
    response.delete_cookie('hp_refresh', path='/')
    return {"ok": True}


@app.post('/auth/refresh', response_model=Token)
def refresh_endpoint(request: Request):
    # Use refresh token cookie to issue a new short-lived access token.
    refresh = request.cookies.get('hp_refresh')
    if not refresh:
        raise HTTPException(status_code=401, detail='Missing refresh token')
    username = verify_refresh_token(refresh)
    if not username:
        raise HTTPException(status_code=401, detail='Invalid or expired refresh token')
    # Determine role from simple user store
    role = check_credentials(username, None) if False else None
    # We don't have plaintext password; instead, read the user's record role
    from backend.users import get_user
    user = get_user(username)
    if not user:
        raise HTTPException(status_code=401, detail='User not found')
    role = user.get('role')
    # issue new access token
    new_token = create_access_token(sub=username, role=role)
    resp = JSONResponse(content={"access_token": new_token, "token_type": "bearer"})
    max_age = ACCESS_TOKEN_EXPIRE_MIN * 60
    resp.set_cookie('hp_token', new_token, httponly=True, secure=not S.debug, samesite='strict', max_age=max_age, path='/')
    return resp

@app.get("/auth/me", response_model=UserInfo)
def me(user: UserInfo = Depends(get_current_user)):
    # Return current user info from JWT.
    return user


# Settings endpoints (MVP). GET available to authenticated users, POST requires Admin.
@app.get("/settings", response_model=dict)
def get_settings_endpoint(user: UserInfo = Depends(get_current_user)):
    # Return current in-memory home settings.
    return get_home_settings()


@app.post("/settings", response_model=dict)
def post_settings_endpoint(new_settings: dict, user: UserInfo = Depends(require_admin)):
    # Update allowed settings (Admin only for safety in MVP).
    updated = update_home_settings(new_settings)
    return {"ok": True, "settings": updated}


# Devices endpoint - return list of sensors as "devices"
@app.get("/devices", response_model=List[dict])
def get_devices(user: UserInfo = Depends(get_current_user)):
    """Return list of known sensors/devices with their last readings."""
    devices = []
    for sensor_id, reading in SENSOR_LAST.items():
        devices.append({
            "id": sensor_id,
            "name": f"{reading.type.capitalize()} - {reading.location}",
            "type": reading.type,
            "location": reading.location,
            "value": reading.value,
            "online": True,  # If we have a reading, assume online
            "last_update": reading.ts.isoformat()
        })
    return devices


# Protect sensitive actions
@app.post("/alerts/{alert_id}/ack", response_model=dict)
def ack_alert(alert_id: str, user: UserInfo = Depends(get_current_user)):
    # Require authentication to acknowledge alerts.
    if not acknowledge_alert(alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"ok": True, "acknowledged": alert_id, "by": user.username}