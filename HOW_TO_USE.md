1. Project Structure
High-Privacy-Smart-Home-Safety-System/
│
├── backend/                # FastAPI server (Edge Hub)
│   ├── main.py             # API entry point
│   ├── logic.py            # Alert logic
│   ├── store.py            # In-memory data store
│   ├── models.py           # Data models
│   ├── config.py           # Config & CORS settings
│   ├── security.py         # Password hashing, JWT utils
│   ├── users.py            # User store (Admin, Occupant)
│   └── requirements.txt    # Backend dependencies
│
├── Simulation/             # Sensor simulator (Python)
│   └── simulation.py
│
├── Front-End-User/         # React or Web front-end (work in progress)
│   └── App.js
│
│
├── README.md
└── HOW_TO_USE.md           # (this file)

2. Environment Setup (First Time Only)
Step 1. Create and activate virtual environment
cd High-Privacy-Smart-Home-Safety-System
py -m venv .venv
.\.venv\Scripts\Activate.ps1

Step 2. Install all dependencies
pip install -r backend/requirements.txt

Step 3. Fix Windows bcrypt issue (already pinned)

bcrypt has been pinned to version 3.2.2 for compatibility with passlib.
If you still get an error, re-run:

pip install bcrypt==3.2.2

3. HTTPS Certificate Setup

Certificates are not committed to GitHub for security.
Each teammate must generate their own self-signed certificate locally.

Generate once with:

# Run this inside the project root
python .\tools\make_selfsigned_cert.py


You should see:

Wrote key.pem and cert.pem


Now you will have two new files:

key.pem
cert.pem

4. Run the Backend (Edge Hub Server)

Run FastAPI with HTTPS:

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8443 `
  --ssl-keyfile=key.pem --ssl-certfile=cert.pem


Visit in browser:

https://127.0.0.1:8443/status


You should see:

{
  "system": "running",
  "sensors_online": 0,
  "alerts_open": 0
}

5. Login / Authentication (JWT)
Available demo accounts
Username	Password	Role
admin	admin123	Admin
alice	alice123	Occupant
How to log in (example using curl)
curl -X POST https://127.0.0.1:8443/auth/login -k ^
-H "Content-Type: application/json" ^
-d "{\"username\":\"admin\",\"password\":\"admin123\"}"


Returns:

{
  "access_token": "<JWT_TOKEN>",
  "token_type": "bearer"
}


Use this token in the header for secure requests:

Authorization: Bearer <JWT_TOKEN>


Example (acknowledge alert):

curl -X POST https://127.0.0.1:8443/alerts/<ALERT_ID>/ack -k ^
-H "Authorization: Bearer <JWT_TOKEN>"

6. Run the Sensor Simulator
Example 1: Continuous mixed simulation
python Simulation/simulation.py --scenario continuous --interval 5

Example 2: Specific scenario test
python Simulation/simulation.py --scenario fire
python Simulation/simulation.py --scenario gas_leak
python Simulation/simulation.py --scenario water_leak
python Simulation/simulation.py --scenario break_in


If using HTTPS, add --base-url https://127.0.0.1:8443 and make sure the simulator disables SSL verification (already supported).

Example:

python Simulation/simulation.py --base-url https://127.0.0.1:8443 --scenario fire

7. Front-End Integration (React)

Fetch /status to display system summary

Fetch /alerts to list all active alerts

POST /auth/login for login form

Include Authorization: Bearer <token> when acknowledging alerts

The CORS settings in backend/config.py already include:

cors_origins = [
    "http://localhost:3000",
    "https://127.0.0.1:8443"
]

8. Testing Accounts & Permissions
Role	Can Acknowledge Alerts	Can Configure Sensors	Can View Alerts
Admin	✅	✅	✅
Occupant	✅	❌	✅
9. Notes for GitHub Version Control

Do NOT commit these files or folders:

.venv/
__pycache__/
key.pem
cert.pem
tools/__pycache__/

Optional: add them to .gitignore

If not already present, create a .gitignore file in project root with:

# Python
__pycache__/
*.pyc

# Virtual environment
.venv/

# Local certs
key.pem
cert.pem

# Tool cache
tools/__pycache__/