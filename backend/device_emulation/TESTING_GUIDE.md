# Device Emulation System - Testing Guide

## Overview
The device emulation system allows you to simulate smart home security devices and test the full discovery, pairing, and event flow.

## Architecture

### Device Emulator (`backend/device_emulation/device.py`)
- FastAPI-based emulated security device
- Supports multiple device types: door, window, garage, gas, co, water, fire, smoke, temp
- Features:
  - Device discovery endpoint (`/discover`)
  - Pairing with shared secret generation (`/pair`)
  - Status queries (`/status`)
  - Configuration (`/configure`)
  - Automatic event generation (optional)
  - End-to-end encryption ready (shared secret)

### Backend Discovery (`backend/device_discovery.py`)
- Scans ports 8080+ for devices
- Pairs with devices and stores credentials
- Configures devices with backend URL
- Retrieves device status

### Backend Endpoints (added to `backend/main.py`)
- `GET /devices/discover` - Scan for devices on network
- `POST /devices/pair` - Pair with a discovered device
- `GET /devices/registered` - List all paired devices
- `DELETE /devices/{device_id}` - Remove a device
- `GET /devices/{device_id}/status` - Get device status

### Frontend Setup Wizard
- New "Device Setup" page in navigation
- Three-step process:
  1. Scan for devices (configurable port range)
  2. Display discovered devices with pairing option
  3. Show registered devices with management options

## Testing Steps

### 1. Install Dependencies
```bash
# Make sure you're in the virtual environment
.venv\Scripts\activate

# Install httpx (newly added)
pip install httpx
```

### 2. Start Multiple Emulated Devices
```bash
cd backend\device_emulation
.\spawn_devices.bat
```

This will open 5 windows, each running a different device:
- Door Sensor - Front Door (port 8080)
- Window Sensor - Kitchen (port 8081)
- Smoke Detector - Living Room (port 8082)
- CO Detector - Garage (port 8083)
- Temperature Sensor - Bedroom (port 8084)

Each device:
- Auto-detects available port
- Shows pairing code
- Sends events automatically every 15-35 seconds
- Waits for pairing from backend

### 3. Start the Backend
```bash
# From project root
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

### 4. Start the Frontend
```bash
cd Front-End-User
python serve_https.py
```

### 5. Test Device Discovery and Pairing

1. **Login** to the frontend (admin/admin123)

2. **Navigate to "Device Setup"** page

3. **Scan for Devices**:
   - Click "Scan for Devices" button
   - Should find all 5 running devices
   - Each device shows:
     - Device ID, type, location
     - Port number
     - Pairing status
     - Optional pairing code field

4. **Pair Devices**:
   - Click "Pair Device" on any discovered device
   - Pairing code is optional (auto-accepted in simulation)
   - Device gets paired and configured with backend URL
   - Success message appears

5. **View Registered Devices**:
   - Click "Refresh" in Step 3
   - Shows all paired devices
   - Displays online status, last reading, current value
   - Option to remove devices

### 6. Test Event Flow

Once devices are paired and configured:

1. Devices automatically send events every 15-35 seconds
2. Backend receives events at `/sensor` endpoint
3. Events are processed by logic.py (creates alerts if needed)
4. Alerts appear on Dashboard
5. Device status updates on Devices page

### 7. Manual Device Testing

You can also run a single device manually:

```bash
cd backend\device_emulation
python device.py --type door --location "Test Door" --auto-events
```

Options:
- `--port 8090` - Specify port (auto-detects if not set)
- `--type door` - Device type
- `--location "Kitchen"` - Device location
- `--auto-events` - Enable automatic event generation
- `--event-interval 20` - Event interval in seconds

### 8. Test API Endpoints Directly

Using curl or Postman:

```bash
# Discover devices
curl -k https://localhost:8000/devices/discover?start_port=8080&count=10 \
  -H "Cookie: hp_token=YOUR_TOKEN"

# Get registered devices
curl -k https://localhost:8000/devices/registered \
  -H "Cookie: hp_token=YOUR_TOKEN"

# Check device at specific port
curl http://localhost:8080/discover

# Get device status
curl http://localhost:8080/status

# Pair with device
curl -X POST http://localhost:8080/pair \
  -H "Content-Type: application/json" \
  -d '{"pairing_code": null}'
```

## Expected Behavior

### Device Lifecycle

1. **Discovery Phase**:
   - Device runs on auto-detected port
   - Responds to `/discover` endpoint
   - Shows as "Not Paired" in frontend

2. **Pairing Phase**:
   - Backend calls `/pair` endpoint
   - Device generates shared secret
   - Backend stores device info and secret
   - Device status changes to "Paired"

3. **Configuration Phase**:
   - Backend calls `/configure` with backend URL
   - Device now knows where to send events

4. **Active Phase**:
   - Device sends events to backend at intervals
   - Backend processes events and creates alerts
   - Frontend displays device status and alerts
   - Last seen timestamp updates

### Security Features

- **Pairing Codes**: Optional 6-digit codes for pairing
- **Shared Secrets**: Generated during pairing for E2E encryption
- **HTTPS**: Backend uses SSL/TLS
- **Authentication**: All management endpoints require login
- **Admin-only**: Pairing and device removal require admin role

## Troubleshooting

### Devices Not Discovered
- Check devices are running (should see console windows)
- Verify port range in scan settings
- Check firewall isn't blocking local connections

### Pairing Fails
- Ensure backend is running with HTTPS
- Check device console for errors
- Verify you're logged in as admin

### Events Not Appearing
- Check device was configured with backend URL
- Verify backend `/sensor` endpoint is working
- Check device console for send errors
- Ensure HTTPS certificate is trusted

### Backend Errors
- Install httpx: `pip install httpx`
- Check all dependencies installed
- Verify database initialized (data.db created)

## Next Steps

Future enhancements could include:
- Actual encryption/decryption of event payloads
- Device authentication tokens
- Heartbeat monitoring
- Device firmware updates
- Remote device configuration
- Device groups and zones
- Network security scanning
