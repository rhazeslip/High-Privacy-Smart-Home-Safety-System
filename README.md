# High-Privacy-Smart-Home-Safety-System
High-Privacy Smart Home Safety System (HP-SHSS)
Edge Hub (Server) Setup and Usage Guide
1. Overview

The Edge Hub is the local backend service of our project.
It receives data from simulated or real sensors, processes them locally, and generates alerts according to the rules defined in our SRS (gas leak, fire, water leak, entry monitoring, etc.).
It runs entirely offline to preserve privacy and only sends alerts to clients.

2. Prerequisites

Python 3.9 or higher

Git installed

Recommended to use a virtual environment (.venv)

3. Project Structure

High-Privacy-Smart-Home-Safety-System/
backend/                  ← Edge Hub (FastAPI backend)
main.py               ← Main FastAPI application
logic.py              ← Core alerting logic
models.py             ← Pydantic data models
store.py              ← In-memory storage
config.py             ← Thresholds and settings
Simulation/               ← Sensor simulation scripts
simulation.py
Front-End-User/           ← React/Vue client (UI)

4. Installation and Setup
Step 1 – Create and activate virtual environment
cd High-Privacy-Smart-Home-Safety-System
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # PowerShell on Windows

Step 2 – Install dependencies
pip install -r backend/requirements.txt

Step 3 – Start the Edge Hub
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000


The console should show:

Uvicorn running on http://0.0.0.0:8000

5. Verify it’s working

Open a browser and visit:

http://127.0.0.1:8000/status


You should see:

{
  "system": "running",
  "sensors_online": 0,
  "alerts_open": 0
}


This confirms the Edge Hub is active.

6. Simulate Sensor Data

To test the system, open another terminal window and run:

.\.venv\Scripts\Activate.ps1
python Simulation/simulation.py


This script sends random readings (door open/closed, gas ppm, smoke, etc.) to the Edge Hub.
You will see log messages like:

-> {'sensor_id': 'co_sensor_basement', 'type': 'co', 'value': 95, 'location': 'Basement'} | resp: {'ok': True, 'alerts_created': 1, 'alert_ids': ['...']}

7. Available API Endpoints
Method	Endpoint	Description
GET	/status	Returns overall system status (health check).
POST	/sensor	Sends a sensor reading to the server.
GET	/alerts	Returns current alerts.
POST	/alerts/{alert_id}/ack	Acknowledge (mark as resolved) a specific alert.
8. Example API Call (manual test)

You can use curl or Postman:

curl -X POST http://127.0.0.1:8000/sensor ^
     -H "Content-Type: application/json" ^
     -d "{\"sensor_id\":\"co_sensor_basement\",\"type\":\"co\",\"value\":120,\"location\":\"Basement\"}"


Expected response:

{"ok": true, "alerts_created": 1, "alert_ids": ["..."]}

9. Next Steps

Front-End Integration:
The React client (Front-End-User/App.js) can call /status and /alerts to display data.

Database or MQTT upgrade:
Replace the in-memory storage (store.py) with SQLite or MQTT for real devices.

Authentication:
Add user login and JWT-based authentication to align with SRS FR-18 to FR-22.

10. Security and HTTPS (recommended)

For a high level of security in local/edge deployments, run the Edge Hub with HTTPS
and use a strong JWT secret set via environment variables. The project includes a
simple self-signed certificate generator in `tools/make_selfsigned_cert.py` and the
repository root contains `cert.pem` and `key.pem` for local testing.

Run uvicorn with TLS:

```powershell
& .\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --ssl-certfile cert.pem --ssl-keyfile key.pem
```

Set a strong JWT secret in the environment before starting the server (this
prevents the server from generating a new secret at each restart):

```powershell
$env:HP_SHSS_JWT_SECRET = 'a-very-long-random-secret'
```

Notes:
- The backend now sets the access token as an HttpOnly, Secure cookie named
  `hp_token`. The frontend should send credentials (cookies) with requests.
- By default access tokens are short-lived (15 minutes). Consider adding a
  refresh-token workflow and persistent server-side revocation storage for
  production.
- In production, use certificates issued by a trusted CA (not self-signed).

11. Stopping the Server

To stop the Edge Hub, press CTRL + C in the terminal where uvicorn is running.