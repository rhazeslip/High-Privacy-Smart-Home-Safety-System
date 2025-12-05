# backend/main.py
# FastAPI app for HP-SHSS Edge Hub

from typing import List, Optional, Dict
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from backend.logic import process_reading
from backend.config import get_settings
from backend.security import create_access_token, decode_token, create_refresh_token, verify_refresh_token, verify_password
from backend.store import revoke_refresh_token
from backend.users import get_admin, verify_admin_password
import time
import threading
import logging
import asyncio
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('hp_shss')
audit_logger = logging.getLogger('hp_shss.audit')

# Rate limiting configuration
RATE_LIMIT_WINDOW = 60  # seconds
MAX_LOGIN_ATTEMPTS = 5  # max attempts per window
MAX_SALT_REQUESTS = 10  # max salt requests per window
MAX_RESET_ATTEMPTS = 3  # max password reset attempts per window

# Thread-safe rate limiting storage
_rate_limit_lock = threading.Lock()
_rate_limits: Dict[str, Dict[str, any]] = {}  # IP -> {"login": (count, window_start), ...}

def _check_rate_limit(ip: str, action: str, max_attempts: int) -> bool:
    """Check if request should be rate limited. Returns True if allowed."""
    now = time.time()
    with _rate_limit_lock:
        if ip not in _rate_limits:
            _rate_limits[ip] = {}
        
        if action not in _rate_limits[ip]:
            _rate_limits[ip][action] = {"count": 1, "window_start": now}
            return True
        
        data = _rate_limits[ip][action]
        # Check if window has expired
        if now - data["window_start"] > RATE_LIMIT_WINDOW:
            _rate_limits[ip][action] = {"count": 1, "window_start": now}
            return True
        
        # Check if under limit
        if data["count"] < max_attempts:
            data["count"] += 1
            return True
        
        return False

def _get_client_ip(request: Request) -> str:
    """Get client IP, considering proxy headers."""
    # Check for forwarded headers (reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

#  Absolute imports so we can run "uvicorn backend.main:app" from project root.
from backend.models import (
    SensorReading, Alert, StatusResponse, LoginRequest, Token, UserInfo,
    SetupStatus, SetupRequest, SetupResponse, PasswordResetRequest, PasswordResetResponse,
    ChangePasswordRequest
)
from backend.store import (
    save_reading, list_alerts, acknowledge_alert, count_open_alerts, SENSOR_LAST, ALERTS,
    is_setup_complete, mark_setup_complete, get_home_name, set_home_name,
    get_recovery_key, set_recovery_key, get_system_config, set_system_config
)
from backend.store import get_home_settings, update_home_settings
from backend.security import ACCESS_TOKEN_EXPIRE_MIN
from fastapi.responses import JSONResponse
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from pydantic import BaseModel


S = get_settings()
app = FastAPI(title=S.project_name, debug=S.debug)

# Request timeout middleware (30 second default)
REQUEST_TIMEOUT = 30.0

class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout: {request.method} {request.url.path}")
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timeout"}
            )

app.add_middleware(TimeoutMiddleware)

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
    """Verify authentication for single admin user."""
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
        if claims.get("sub") != "admin":
            raise ValueError("Invalid token")
        return UserInfo(authenticated=True)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# Simplified: all authenticated users are admin
require_admin = get_current_user

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
        # Ensure Content-Type has UTF-8 charset for JSON responses
        if 'content-type' in resp.headers and resp.headers['content-type'].startswith('application/json'):
            resp.headers['content-type'] = 'application/json; charset=utf-8'
        return resp
else:
    # Add security headers even in debug mode
    @app.middleware("http")
    async def debug_security_headers_middleware(request: Request, call_next):
        resp = await call_next(request)
        resp.headers['X-Frame-Options'] = 'DENY'
        resp.headers['X-Content-Type-Options'] = 'nosniff'
        resp.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
        return resp


# Health check response model
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str = "1.0.0"
    database: str = "ok"


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint for monitoring."""
    # Basic database connectivity check
    db_status = "ok"
    try:
        from backend.store import _DB
        _DB.execute("SELECT 1")
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error(f"Database health check failed: {e}")
    
    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        database=db_status
    )


# Audit logging helper
def audit_log(action: str, ip: str, details: str = "", success: bool = True):
    """Log security-relevant events."""
    if S.audit_log:
        status = "SUCCESS" if success else "FAILED"
        audit_logger.info(f"[{status}] {action} from {ip} - {details}")


# Setup wizard endpoints (publicly accessible before setup is complete)
@app.get("/setup/status", response_model=SetupStatus)
def get_setup_status():
    """Check if initial setup has been completed"""
    return SetupStatus(
        setup_complete=is_setup_complete(),
        home_name=get_home_name() if is_setup_complete() else None
    )

@app.post("/setup/complete", response_model=SetupResponse)
def complete_setup(setup: SetupRequest):
    """Complete initial setup wizard"""
    # Check if setup already completed
    if is_setup_complete():
        raise HTTPException(status_code=400, detail="Setup already completed")
    
    # Validate passwords match
    if setup.admin_password != setup.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    # Validate password strength
    if len(setup.admin_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Generate recovery key (16 random words or UUID-based key)
    import secrets
    recovery_key = secrets.token_urlsafe(32)  # 43-character base64url string
    
    # Generate salt for password hashing
    import hashlib
    import base64
    import os
    from backend.security import hash_password, hash_recovery_key
    from backend.store import db_set_admin_password
    
    salt = os.urandom(16)
    salt_b64 = base64.b64encode(salt).decode()
    
    # Derive client-side hash simulation (in real app, client would do this)
    client_hash = hashlib.pbkdf2_hmac('sha256', setup.admin_password.encode(), salt, 100000).hex()
    hashed_password = hash_password(client_hash)
    
    # Store admin credentials in system_config
    db_set_admin_password(hashed_password, salt_b64)
    
    # Store system configuration - hash the recovery key before storing
    set_home_name(setup.home_name)
    set_recovery_key(hash_recovery_key(recovery_key))  # Store hashed, not plaintext
    mark_setup_complete()
    
    return SetupResponse(
        success=True,
        recovery_key=recovery_key,
        message="Setup completed successfully. Please save your recovery key in a secure location."
    )

@app.post("/auth/reset-password", response_model=PasswordResetResponse)
def reset_password(reset_req: PasswordResetRequest, request: Request):
    """Reset password using recovery key"""
    # Rate limiting - very strict for password reset
    client_ip = _get_client_ip(request)
    if not _check_rate_limit(client_ip, "reset", MAX_RESET_ATTEMPTS):
        audit_log("PASSWORD_RESET", client_ip, "Rate limited", success=False)
        raise HTTPException(
            status_code=429,
            detail="Too many password reset attempts. Please try again later."
        )
    
    # Check if setup is complete
    if not is_setup_complete():
        raise HTTPException(status_code=400, detail="System setup not completed")
    
    # Validate passwords match
    if reset_req.new_password != reset_req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    # Validate password strength
    if len(reset_req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Verify recovery key (stored key is hashed)
    from backend.security import verify_recovery_key
    stored_key_hash = get_recovery_key()
    if not stored_key_hash or not verify_recovery_key(reset_req.recovery_key, stored_key_hash):
        # Add delay to slow down brute force attempts
        import time
        time.sleep(1)
        audit_log("PASSWORD_RESET", client_ip, "Invalid recovery key", success=False)
        raise HTTPException(status_code=401, detail="Invalid recovery key")
    
    # Generate new password hash
    import hashlib
    import base64
    import os
    from backend.security import hash_password
    from backend.store import db_get_admin, db_set_admin_password
    
    # Get existing admin to preserve salt or generate new one
    admin = db_get_admin()
    if admin and admin.get('salt'):
        salt_b64 = admin['salt']
        salt = base64.b64decode(salt_b64)
    else:
        # Generate new salt if somehow missing
        salt = os.urandom(16)
        salt_b64 = base64.b64encode(salt).decode()
    
    # Derive client-side hash simulation
    client_hash = hashlib.pbkdf2_hmac('sha256', reset_req.new_password.encode(), salt, 100000).hex()
    hashed_password = hash_password(client_hash)
    
    # Update password in system_config
    db_set_admin_password(hashed_password, salt_b64)
    
    audit_log("PASSWORD_RESET", client_ip, "Password reset successful")
    
    return PasswordResetResponse(
        success=True,
        message="Password reset successfully. Please login with your new password."
    )

@app.post("/auth/change-password", response_model=PasswordResetResponse)
def change_password(change_req: ChangePasswordRequest, user: UserInfo = Depends(get_current_user)):
    """Change password for admin user"""
    from backend.security import hash_password, verify_password
    from backend.store import db_get_admin, db_set_admin_password
    import hashlib
    import base64
    import os
    
    # Get admin credentials
    admin = db_get_admin()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not configured")
    
    # Verify current password
    stored_hash = admin.get('hashed_pw')
    if not stored_hash:
        raise HTTPException(status_code=400, detail="No password set")
    
    if not verify_password(change_req.current_password_hash, stored_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    # Validate new password strength
    if len(change_req.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    
    # Get admin's salt
    salt_b64 = admin.get('salt')
    if not salt_b64:
        # Generate new salt if missing
        salt = os.urandom(16)
        salt_b64 = base64.b64encode(salt).decode()
    else:
        salt = base64.b64decode(salt_b64)
    
    # Derive client-side hash for new password
    new_client_hash = hashlib.pbkdf2_hmac('sha256', change_req.new_password.encode(), salt, 100000).hex()
    new_hashed_password = hash_password(new_client_hash)
    
    # Update password in system_config
    db_set_admin_password(new_hashed_password, salt_b64)
    
    return PasswordResetResponse(
        success=True,
        message="Password changed successfully"
    )

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
def ingest_sensor(reading: SensorReading, request: Request):
    """Ingest a sensor reading. Requires device authentication via shared secret."""
    from backend.store import get_device
    import hmac
    import hashlib
    
    # Verify device is registered and paired
    device = get_device(reading.sensor_id)
    if not device:
        raise HTTPException(status_code=401, detail="Unknown device")
    
    if not device.get('paired'):
        raise HTTPException(status_code=401, detail="Device not paired")
    
    # Verify device authentication via X-Device-Auth header
    # Format: HMAC-SHA256 of sensor_id + timestamp, using shared_secret
    auth_header = request.headers.get('X-Device-Auth')
    timestamp_header = request.headers.get('X-Device-Timestamp')
    
    if device.get('shared_secret'):
        if not auth_header or not timestamp_header:
            raise HTTPException(status_code=401, detail="Device authentication required")
        
        # Check timestamp is within 5 minutes to prevent replay attacks
        try:
            req_time = datetime.fromisoformat(timestamp_header.replace('Z', '+00:00'))
            now = datetime.utcnow().replace(tzinfo=req_time.tzinfo) if req_time.tzinfo else datetime.utcnow()
            if abs((now - req_time).total_seconds()) > 300:
                raise HTTPException(status_code=401, detail="Request timestamp expired")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid timestamp format")
        
        # Verify HMAC
        expected_sig = hmac.new(
            device['shared_secret'].encode(),
            f"{reading.sensor_id}{timestamp_header}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(auth_header, expected_sig):
            raise HTTPException(status_code=401, detail="Invalid device authentication")
    
    # Ingest the reading
    save_reading(reading)
    
    # Update device last_seen timestamp
    from backend.store import update_device_last_seen
    update_device_last_seen(reading.sensor_id)
    
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
def login(req: LoginRequest, request: Request):
    """Login with password (single admin user)"""
    # Rate limiting check
    client_ip = _get_client_ip(request)
    if not _check_rate_limit(client_ip, "login", MAX_LOGIN_ATTEMPTS):
        audit_log("LOGIN", client_ip, "Rate limited", success=False)
        raise HTTPException(
            status_code=429, 
            detail="Too many login attempts. Please try again later."
        )
    
    # Check if setup is complete
    if not is_setup_complete():
        raise HTTPException(status_code=400, detail="System setup not completed")
    
    from backend.store import db_get_admin
    
    # If client_hash provided, verify against stored bcrypt hash
    if req.client_hash:
        admin = db_get_admin()
        if not admin:
            audit_log("LOGIN", client_ip, "No admin configured", success=False)
            raise HTTPException(status_code=401, detail="Invalid password")
        # stored hashed_pw is bcrypt() of client_hash
        if not verify_password(req.client_hash, admin['hashed_pw']):
            audit_log("LOGIN", client_ip, "Invalid password", success=False)
            raise HTTPException(status_code=401, detail="Invalid password")
    else:
        # Fallback: legacy password field (plaintext) - convert to client_hash
        if req.password:
            import hashlib
            import base64
            admin = db_get_admin()
            if not admin or not admin.get('salt'):
                audit_log("LOGIN", client_ip, "No admin configured", success=False)
                raise HTTPException(status_code=401, detail="Invalid password")
            
            salt = base64.b64decode(admin['salt'])
            client_hash = hashlib.pbkdf2_hmac('sha256', req.password.encode(), salt, 100000).hex()
            
            if not verify_password(client_hash, admin['hashed_pw']):
                audit_log("LOGIN", client_ip, "Invalid password (legacy)", success=False)
                raise HTTPException(status_code=401, detail="Invalid password")
        else:
            audit_log("LOGIN", client_ip, "No password provided", success=False)
            raise HTTPException(status_code=401, detail="Password required")
    
    audit_log("LOGIN", client_ip, "Successful login")
    
    token = create_access_token()
    # Set HttpOnly, Secure cookie for the token (frontend will use cookie-based auth).
    resp = JSONResponse(content={"access_token": token, "token_type": "bearer"})
    # Max-Age in seconds
    max_age = ACCESS_TOKEN_EXPIRE_MIN * 60
    resp.set_cookie(
        key='hp_token',
        value=token,
        httponly=True,
        secure=True,  # Always use secure cookies with HTTPS
        samesite='lax',
        max_age=max_age,
        path='/'
    )
    # Also create a long-lived refresh token (HttpOnly cookie) so clients can
    # obtain new access tokens without re-prompting credentials.
    refresh_token, refresh_exp = create_refresh_token()
    # Simpler: set refresh cookie max-age to 7 days by default
    # Use 'strict' SameSite for refresh tokens for better security
    resp.set_cookie(
        key='hp_refresh',
        value=refresh_token,
        httponly=True,
        secure=True,  # Always use secure cookies with HTTPS
        samesite='strict',  # Strict for refresh tokens
        max_age=7*24*3600,
        path='/'
    )
    return resp


@app.get('/auth/salt')
def get_salt(request: Request = None):
    """Get salt for admin password hashing"""
    # Rate limiting to prevent enumeration attacks
    if request:
        client_ip = _get_client_ip(request)
        if not _check_rate_limit(client_ip, "salt", MAX_SALT_REQUESTS):
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later."
            )
    
    # Return admin salt from system_config
    from backend.store import db_get_admin
    import os
    import base64
    import time
    
    admin = db_get_admin()
    
    # Add random delay to prevent timing attacks (50-150ms)
    time.sleep(0.05 + (int.from_bytes(os.urandom(1), 'big') / 2550))
    
    if not admin or not admin.get('salt'):
        # Return a fake salt if admin not set up yet
        import hashlib
        fake_seed = hashlib.sha256(b"fake_salt_admin").digest()[:16]
        fake_salt = base64.b64encode(fake_seed).decode()
        return { 'salt': fake_salt }
    
    return { 'salt': admin.get('salt') }


# (original definitions moved earlier in the file)


@app.post('/auth/logout')
def logout(request: Request, response: Response):
    # Clear the auth cookie on logout and revoke refresh token if present.
    client_ip = _get_client_ip(request)
    audit_log("LOGOUT", client_ip, "User logged out")
    response.delete_cookie('hp_token', path='/')
    # Attempt to revoke refresh token if client sent it.
    # Note: in FastAPI you can read cookies from the Request object; use a
    # small helper to avoid changing signature here. If the client doesn't
    # send the refresh cookie, just clear the cookie on the response.
    return {"ok": True}


@app.post('/auth/logout_full')
def logout_full(request: Request, response: Response):
    # Clear cookies and revoke refresh token stored server-side.
    client_ip = _get_client_ip(request)
    refresh = request.cookies.get('hp_refresh')
    if refresh:
        try:
            revoke_refresh_token(refresh)
        except Exception:
            pass
    audit_log("LOGOUT_FULL", client_ip, "Full logout with token revocation")
    response.delete_cookie('hp_token', path='/')
    response.delete_cookie('hp_refresh', path='/')
    return {"ok": True}


@app.post('/auth/refresh', response_model=Token)
def refresh_endpoint(request: Request):
    # Use refresh token cookie to issue a new short-lived access token.
    refresh = request.cookies.get('hp_refresh')
    if not refresh:
        raise HTTPException(status_code=401, detail='Missing refresh token')
    if not verify_refresh_token(refresh):
        raise HTTPException(status_code=401, detail='Invalid or expired refresh token')
    # Issue new access token for admin
    new_token = create_access_token()
    resp = JSONResponse(content={"access_token": new_token, "token_type": "bearer"})
    max_age = ACCESS_TOKEN_EXPIRE_MIN * 60
    resp.set_cookie('hp_token', new_token, httponly=True, secure=not S.debug, samesite='strict', max_age=max_age, path='/')
    return resp

@app.get("/auth/me", response_model=UserInfo)
def me(user: UserInfo = Depends(get_current_user)):
    # Return current user info (simplified - just authenticated status).
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
    return {"ok": True, "acknowledged": alert_id}


# Device Discovery and Management Endpoints
@app.get("/devices/discover")
async def discover_devices_endpoint(
    start_port: int = 8080, 
    count: int = 20,
    user: UserInfo = Depends(get_current_user)
):
    """Scan for devices on local network starting from start_port"""
    from backend.device_discovery import discover_devices
    devices = await discover_devices(start_port=start_port, count=count, timeout=0.5)
    return {"devices": devices, "scanned_ports": count}


@app.post("/devices/pair")
async def pair_device_endpoint(
    request: dict,
    user: UserInfo = Depends(require_admin)
):
    """Pair with a discovered device"""
    from backend.device_discovery import pair_device, configure_device
    from backend.store import save_device, get_device
    from backend.config import get_settings
    
    device_id = request.get('device_id')
    port = request.get('port')
    pairing_code = request.get('pairing_code')
    user_name = request.get('name')  # User-defined name
    user_location = request.get('location')  # User-defined location
    
    if not device_id or not port:
        raise HTTPException(status_code=400, detail="device_id and port are required")
    
    # Attempt to pair
    result = await pair_device(port, pairing_code)
    if not result or not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('message', 'Pairing failed') if result else 'Pairing failed - no response from device')
    
    # Get device info to save
    import httpx
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            info_response = await client.get(f"http://127.0.0.1:{port}/info")
            device_info = info_response.json()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to get device info")
    
    # Use user-provided name and location if given, otherwise use device defaults
    device_name = user_name if user_name else device_info.get('name', f"{device_info['type']} Sensor")
    device_location = user_location if user_location else device_info.get('location', 'Unknown')
    
    # Save device to database
    save_device(
        device_id=result['device_id'],
        name=device_name,
        device_type=device_info['type'],
        location=device_location,
        port=port,
        paired=True,
        shared_secret=result.get('shared_secret'),
        model=device_info.get('model', 'HP-SHSS-SIM'),
        firmware_version=device_info.get('firmware_version', '1.0.0')
    )
    
    # Configure device with backend URL
    settings = get_settings()
    backend_url = f"https://localhost:8000"  # Adjust based on your setup
    await configure_device(port, backend_url)
    
    return {
        "success": True,
        "device_id": result['device_id'],
        "message": "Device paired and configured successfully"
    }


@app.get("/devices/registered")
async def get_registered_devices(user: UserInfo = Depends(get_current_user)):
    """Get all registered/paired devices"""
    from backend.store import get_all_devices
    from datetime import datetime, timedelta
    
    try:
        devices = get_all_devices()
        
        print(f"[DEBUG] get_registered_devices returning {len(devices)} devices")
        
        # Consider a device online if it has sent data in the last 5 minutes
        from datetime import timezone
        online_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        # Get battery levels from memory
        battery_levels = globals().get('battery_levels', {})
        
        # Enhance with current status if available
        for device in devices:
            # Add battery level if available
            if device['device_id'] in battery_levels:
                device['battery'] = battery_levels[device['device_id']]
            
            # Check if we have recent sensor reading
            if device['device_id'] in SENSOR_LAST:
                reading = SENSOR_LAST[device['device_id']]
                device['current_value'] = reading.value
                device['last_reading'] = reading.ts.isoformat()
                # Check if reading is recent enough to consider device online
                # Make both datetimes timezone-aware for comparison
                if hasattr(reading.ts, 'tzinfo') and reading.ts.tzinfo is not None:
                    device['online'] = reading.ts >= online_threshold
                else:
                    # If reading.ts is naive, make it UTC-aware
                    from datetime import timezone as tz
                    reading_ts_aware = reading.ts.replace(tzinfo=tz.utc)
                    device['online'] = reading_ts_aware >= online_threshold
            else:
                device['online'] = False
        
        return devices
    except Exception as e:
        print(f"[ERROR] get_registered_devices failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/devices/{device_id}")
async def update_device(
    device_id: str,
    request: dict,
    user: UserInfo = Depends(require_admin)
):
    """Update device name and location"""
    from backend.store import get_device, save_device
    
    device = get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get updated values or keep existing
    name = request.get('name', device['name'])
    location = request.get('location', device['location'])
    
    # Update device in database
    save_device(
        device_id=device_id,
        name=name,
        device_type=device['type'],
        location=location,
        port=device['port'],
        paired=device['paired'],
        shared_secret=device.get('shared_secret'),
        model=device.get('model', 'HP-SHSS-SIM'),
        firmware_version=device.get('firmware_version', '1.0.0')
    )
    
    return {"success": True, "message": "Device updated"}


@app.post("/devices/{device_id}/unpair")
async def unpair_device(device_id: str, user: UserInfo = Depends(require_admin)):
    """Unpair a device (mark as unpaired but keep in database)"""
    from backend.store import get_device, save_device
    import httpx
    
    device = get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Notify the device it's being unpaired
    if device['port']:
        try:
            async with httpx.AsyncClient(verify=False, timeout=2.0) as client:
                await client.post(f"http://127.0.0.1:{device['port']}/unpair")
        except Exception as e:
            # Device might be offline, continue anyway
            pass
    
    # Update device to unpaired status
    save_device(
        device_id=device_id,
        name=device['name'],
        device_type=device['type'],
        location=device['location'],
        port=device['port'],
        paired=False,
        shared_secret=None,  # Clear the shared secret
        model=device.get('model', 'HP-SHSS-SIM'),
        firmware_version=device.get('firmware_version', '1.0.0')
    )
    
    return {"success": True, "message": "Device unpaired"}


@app.post("/devices/refresh")
async def refresh_device_status(user: UserInfo = Depends(get_current_user)):
    """Ping all paired devices to get their current status"""
    from backend.store import get_all_devices, update_device_last_seen
    from datetime import datetime, timezone
    import httpx
    
    devices = get_all_devices()
    updated_count = 0
    
    async with httpx.AsyncClient(verify=False, timeout=2.0) as client:
        for device in devices:
            if not device['paired'] or not device['port']:
                continue
                
            try:
                # Get current status from device
                response = await client.get(f"http://127.0.0.1:{device['port']}/status")
                if response.status_code == 200:
                    status = response.json()
                    
                    # Store battery level in memory
                    if 'battery' in status:
                        if 'battery_levels' not in globals():
                            globals()['battery_levels'] = {}
                        globals()['battery_levels'][device['device_id']] = status['battery']
                    
                    # Create sensor reading from device status
                    reading = SensorReading(
                        sensor_id=device['device_id'],
                        type=device['type'],
                        value=status['value'],
                        location=device['location'],
                        ts=datetime.fromisoformat(status['timestamp']) if 'timestamp' in status else datetime.now(timezone.utc)
                    )
                    
                    # Save the reading
                    save_reading(reading)
                    update_device_last_seen(device['device_id'])
                    updated_count += 1
            except Exception as e:
                # Device offline or unreachable
                continue
    
    return {"success": True, "updated": updated_count, "total": len([d for d in devices if d['paired']])}


@app.post("/devices/{device_id}/repair")
async def repair_device_endpoint(
    device_id: str,
    request: dict,
    user: UserInfo = Depends(require_admin)
):
    """Re-pair an unpaired device"""
    from backend.device_discovery import pair_device, configure_device
    from backend.store import save_device, get_device
    from backend.config import get_settings
    
    device = get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    port = request.get('port', device['port'])
    pairing_code = request.get('pairing_code')
    
    if not pairing_code:
        raise HTTPException(status_code=400, detail="pairing_code is required")
    
    # Attempt to pair
    result = await pair_device(port, pairing_code)
    if not result or not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('message', 'Pairing failed') if result else 'Pairing failed - no response from device')
    
    # Get device info to update
    import httpx
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            info_response = await client.get(f"http://127.0.0.1:{port}/info")
            device_info = info_response.json()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to get device info")
    
    # Update device to paired status
    save_device(
        device_id=device_id,
        name=device['name'],  # Keep existing name
        device_type=device_info['type'],
        location=device['location'],  # Keep existing location
        port=port,
        paired=True,
        shared_secret=result.get('shared_secret'),
        model=device_info.get('model', 'HP-SHSS-SIM'),
        firmware_version=device_info.get('firmware_version', '1.0.0')
    )
    
    # Configure device with backend URL
    settings = get_settings()
    backend_url = f"https://localhost:8000"
    await configure_device(port, backend_url)
    
    return {
        "success": True,
        "device_id": device_id,
        "message": "Device repaired successfully"
    }


@app.delete("/devices/{device_id}")
async def remove_device(device_id: str, user: UserInfo = Depends(require_admin)):
    """Remove a device from the system"""
    from backend.store import delete_device
    success = delete_device(device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"success": True, "message": "Device removed"}


@app.get("/devices/{device_id}/status")
async def get_device_status_endpoint(device_id: str, user: UserInfo = Depends(get_current_user)):
    """Get current status from a specific device"""
    from backend.store import get_device, update_device_last_seen
    from backend.device_discovery import get_device_status
    
    device = get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Query device for current status
    status = await get_device_status(device['port'])
    if status:
        update_device_last_seen(device_id)
        return status
    else:
        raise HTTPException(status_code=503, detail="Device not responding")
