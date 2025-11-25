# Device Emulation System - Quick Start

## What Was Built

A complete device discovery, pairing, and event system for the HP-SHSS smart home security platform:

✅ **Emulated Security Devices** - Simulates door, window, smoke, CO, temperature, and other sensors  
✅ **Network Discovery** - Scans ports 8080+ to find devices on the local network  
✅ **Secure Pairing** - Pairs devices with shared secret generation for encryption  
✅ **Event Sending** - Devices automatically send sensor readings to the backend  
✅ **Frontend Setup Wizard** - User-friendly interface to discover and configure devices  
✅ **Database Storage** - Persists device information and credentials  
✅ **Device Management** - Add, remove, and monitor devices through the UI  

## How to Use

### 1. Start Multiple Test Devices
```bash
cd backend\device_emulation
.\spawn_devices.bat
```
This opens 5 terminal windows, each running a different sensor type.

### 2. Start the Backend
```bash
python -m uvicorn backend.main:app --reload --ssl-keyfile key.pem --ssl-certfile cert.pem
```

### 3. Start the Frontend
```bash
cd Front-End-User
python serve_https.py
```

### 4. Use the Setup Wizard
1. Login with `admin` / `admin123`
2. Navigate to **Device Setup** in the sidebar
3. Click **Scan for Devices** (searches ports 8080-8100)
4. Click **Pair Device** on any discovered device
5. View paired devices in Step 3
6. Go to **Dashboard** to see events coming from devices

## Key Files

| File | Purpose |
|------|---------|
| `backend/device_emulation/device.py` | Device emulator (FastAPI app) |
| `backend/device_emulation/spawn_devices.bat` | Launch 5 test devices |
| `backend/device_discovery.py` | Network scanning and pairing logic |
| `backend/main.py` | New `/devices/*` API endpoints |
| `backend/store.py` | Device database storage |
| `Front-End-User/index.html` | Setup wizard page (Step 1-3) |
| `Front-End-User/js/app.js` | Device management UI logic |
| `Front-End-User/js/api.js` | Device API client methods |

## Device Types Supported

- **door** - Door sensor (open/closed)
- **window** - Window sensor (open/closed)
- **garage** - Garage door sensor (open/closed)
- **smoke** - Smoke detector (0.0-1.0)
- **fire** - Fire detector (0.0-1.0)
- **co** - Carbon monoxide (ppm)
- **gas** - Gas leak detector (ppm)
- **water** - Water leak detector (0/1)
- **temp** - Temperature sensor (°C)

## Manual Device Testing

Run a single device with custom settings:
```bash
cd backend\device_emulation
python device.py --type smoke --location "Bedroom" --auto-events --event-interval 15
```

Options:
- `--port 8090` - Specific port (auto-detects if omitted)
- `--type door` - Sensor type
- `--location "Kitchen"` - Location name
- `--auto-events` - Enable automatic event generation
- `--event-interval 20` - Seconds between events

## Event Flow

```
Device (port 8080)
    ↓ sensor reading (e.g., door opens)
    ↓ POST /sensor
Backend (port 8000)
    ↓ processes event
    ↓ creates alert if threshold exceeded
    ↓ stores in database
Frontend
    ↓ fetches alerts every 3 seconds
    ↓ displays on dashboard
```

## Security Features

- ✅ **Pairing Codes** - Optional 6-digit codes
- ✅ **Shared Secrets** - Generated during pairing for E2E encryption
- ✅ **HTTPS** - Backend uses SSL/TLS
- ✅ **Authentication** - All endpoints require login
- ✅ **Admin-only** - Pairing and removal require admin role
- ✅ **Database Storage** - Secure credential storage

## Troubleshooting

**"No devices found"**  
→ Make sure spawn_devices.bat is running (you should see 5 terminal windows)

**"Pairing failed"**  
→ Ensure you're logged in as admin (not alice)

**"Events not appearing"**  
→ Check device console shows "✓ Event sent" messages  
→ Verify devices were paired successfully  

**"Import error: httpx"**  
→ Run: `pip install httpx`

## Documentation

- 📘 **DEVICE_SYSTEM_README.md** - Complete architecture and API reference
- 📗 **TESTING_GUIDE.md** - Detailed testing instructions
- 📙 **Main README.md** - Project overview

## What's Next?

The system is fully functional! You can:

1. **Test the full flow**: Spawn devices → Scan → Pair → Watch events
2. **Create custom devices**: Run single devices with specific configurations
3. **Integrate with alerts**: Events trigger alerts based on `logic.py` rules
4. **Monitor status**: View device online/offline status in real-time
5. **Manage devices**: Add/remove devices through the UI

All devices auto-generate events, so once paired you'll see:
- Temperature changes
- Doors opening/closing  
- Smoke detector readings
- CO levels fluctuating
- Alerts created when thresholds exceeded

Enjoy! 🏠🔒
