# Device Emulation and Discovery System

## Overview

This implementation adds a comprehensive device emulation and discovery system to the HP-SHSS (High-Privacy Smart Home Safety System). The system allows you to simulate security devices, discover them on the network, pair them securely, and receive events.

## Features Implemented

### 1. Emulated Security Devices (`backend/device_emulation/device.py`)

A fully-functional FastAPI-based device emulator that simulates smart home security sensors:

**Supported Device Types:**
- Door sensors
- Window sensors  
- Garage door sensors
- Gas detectors (CO, natural gas)
- Water leak detectors
- Fire/smoke detectors
- Temperature sensors

**Device Capabilities:**
- **Discovery**: Responds to network discovery requests
- **Pairing**: Secure pairing with shared secret generation
- **Status Queries**: Provides current sensor status on demand
- **Event Generation**: Automatically generates and sends sensor events
- **Configuration**: Accepts backend URL configuration
- **Auto-port Detection**: Automatically finds available ports starting at 8080

**Security Features:**
- Pairing codes (6-digit)
- Shared secret generation for end-to-end encryption
- Device authentication ready

**Usage:**
```bash
# Run a single device
python device.py --type door --location "Front Door" --auto-events

# Specify port
python device.py --port 8090 --type smoke --location "Bedroom"

# Custom event interval
python device.py --type temp --location "Kitchen" --auto-events --event-interval 15
```

### 2. Device Discovery Service (`backend/device_discovery.py`)

Backend service that scans the local network for emulated devices:

**Functions:**
- `discover_devices(start_port, count, timeout)` - Scan port range for devices
- `pair_device(port, pairing_code)` - Pair with a discovered device
- `configure_device(port, backend_url)` - Configure device with backend URL
- `get_device_status(port)` - Query device for current status

**Features:**
- Parallel port scanning for speed
- Configurable timeouts
- Automatic device information retrieval
- Error handling and retry logic

### 3. Backend API Endpoints (`backend/main.py`)

New REST endpoints for device management:

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/devices/discover` | GET | Scan network for devices | Yes |
| `/devices/pair` | POST | Pair with discovered device | Admin |
| `/devices/registered` | GET | List all paired devices | Yes |
| `/devices/{device_id}` | DELETE | Remove device | Admin |
| `/devices/{device_id}/status` | GET | Get device status | Yes |

**Request Examples:**
```bash
# Discover devices
GET /devices/discover?start_port=8080&count=20

# Pair device
POST /devices/pair
{
  "device_id": "door_8080",
  "port": 8080,
  "pairing_code": "123456"  // optional
}

# Get registered devices
GET /devices/registered
```

### 4. Database Schema (`backend/store.py`)

New `devices` table for persistent device storage:

**Schema:**
```sql
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    location TEXT,
    port INTEGER,
    paired INTEGER DEFAULT 0,
    shared_secret TEXT,
    model TEXT,
    firmware_version TEXT,
    added_at TEXT,
    last_seen TEXT
)
```

**Store Functions:**
- `save_device()` - Save/update device
- `get_device()` - Retrieve device by ID
- `get_all_devices()` - List all devices
- `update_device_last_seen()` - Update activity timestamp
- `delete_device()` - Remove device

### 5. Frontend Setup Wizard (`Front-End-User/`)

New "Device Setup" page with three-step wizard:

**Step 1: Scan for Devices**
- Configurable start port and range
- Real-time scan status
- Found device count

**Step 2: Discovered Devices**
- Device cards showing:
  - Device ID, type, location
  - Port number
  - Model and firmware version
  - Pairing status
- One-click pairing with optional pairing code
- Visual feedback for pairing status

**Step 3: Registered Devices**
- List of all paired devices
- Online/offline status indicators
- Current sensor values
- Last reading timestamps
- Device removal capability
- Refresh functionality

**UI Components:**
- Responsive grid layout
- Color-coded device cards
- Status badges (online/offline)
- Action buttons (pair, remove)
- Empty states
- Loading indicators

### 6. Frontend API Client (`Front-End-User/js/api.js`)

Extended API client with device management methods:

```javascript
// Discovery and pairing
await api.discoverDevices(startPort, count);
await api.pairDevice(deviceId, port, pairingCode);

// Device management  
await api.getRegisteredDevices();
await api.removeDevice(deviceId);
await api.getDeviceStatus(deviceId);
```

### 7. Batch Spawner (`backend/device_emulation/spawn_devices.bat`)

Convenience script to launch multiple devices for testing:

**Spawns 5 devices:**
1. Door Sensor - Front Door
2. Window Sensor - Kitchen
3. Smoke Detector - Living Room
4. CO Detector - Garage
5. Temperature Sensor - Bedroom

Each opens in a separate terminal window with auto-events enabled.

## Architecture

```
┌─────────────────┐
│   Frontend UI   │
│  Setup Wizard   │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Backend API    │◄────►│  Device Storage  │
│  /devices/*     │      │  (SQLite DB)     │
└────────┬────────┘      └──────────────────┘
         │ HTTP
         ▼
┌─────────────────┐
│ Device Discovery│
│    Service      │
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┐
    ▼         ▼        ▼        ▼
┌────────┐┌────────┐┌────────┐┌────────┐
│Device 1││Device 2││Device 3││Device N│
│:8080   ││:8081   ││:8082   ││:808x   │
└────────┘└────────┘└────────┘└────────┘
```

## Event Flow

1. **Device Discovery:**
   - User clicks "Scan for Devices"
   - Frontend calls `/devices/discover`
   - Backend scans ports 8080-8100
   - Devices respond with info
   - Results displayed in UI

2. **Device Pairing:**
   - User clicks "Pair Device"
   - Frontend calls `/devices/pair`
   - Backend sends pairing request to device
   - Device generates shared secret
   - Backend stores device info and secret
   - Backend configures device with backend URL
   - Success message shown

3. **Event Sending:**
   - Paired device generates events (e.g., door opens)
   - Device POSTs event to `/sensor` endpoint
   - Backend processes event via `logic.py`
   - Alerts created if thresholds exceeded
   - Frontend displays alerts on dashboard
   - Device status updates

4. **Status Monitoring:**
   - Frontend requests device status
   - Backend queries device via HTTP
   - Device returns current sensor value
   - Last seen timestamp updated
   - Status displayed in UI

## Security Considerations

### Implemented:
- ✅ HTTPS for backend API
- ✅ Authentication required for all device endpoints
- ✅ Admin role required for pairing/removal
- ✅ Shared secrets generated during pairing
- ✅ Device credentials stored securely in database
- ✅ Pairing codes for device authorization

### Future Enhancements:
- 🔲 Encrypt event payloads using shared secret
- 🔲 Device authentication tokens
- 🔲 Certificate-based device identity
- 🔲 Rate limiting for discovery scans
- 🔲 Network segmentation recommendations
- 🔲 Automatic device certificate rotation

## Testing

See `backend/device_emulation/TESTING_GUIDE.md` for comprehensive testing instructions.

**Quick Test:**
```bash
# 1. Start devices
cd backend\device_emulation
.\spawn_devices.bat

# 2. Start backend
python -m uvicorn backend.main:app --reload --ssl-keyfile key.pem --ssl-certfile cert.pem

# 3. Start frontend
cd Front-End-User
python serve_https.py

# 4. Login and navigate to Device Setup page
# 5. Click "Scan for Devices"
# 6. Pair discovered devices
# 7. Watch events appear on dashboard
```

## Files Modified/Created

### Created:
- `backend/device_emulation/device.py` - Device emulator
- `backend/device_emulation/spawn_devices.bat` - Multi-device launcher
- `backend/device_emulation/TESTING_GUIDE.md` - Testing documentation
- `backend/device_discovery.py` - Discovery service
- `backend/device_emulation/DEVICE_SYSTEM_README.md` - This file

### Modified:
- `backend/main.py` - Added device endpoints
- `backend/store.py` - Added device storage functions and schema
- `backend/requirements.txt` - Added httpx dependency
- `Front-End-User/index.html` - Added setup wizard page
- `Front-End-User/js/app.js` - Added device management logic
- `Front-End-User/js/api.js` - Added device API methods
- `Front-End-User/css/components.css` - Added setup wizard styles

## Dependencies

New dependency added:
- `httpx` - For async HTTP requests in device discovery

Install with:
```bash
pip install httpx
```

## Configuration

### Backend Configuration
No additional configuration required. Uses existing settings from `backend/config.py`.

### Device Configuration
Devices auto-configure:
- Port: Auto-detected starting at 8080
- Backend URL: Configured during pairing
- Event interval: Default 30s (configurable via CLI)

### Frontend Configuration
API base URL auto-detected from window.location, defaults to `https://127.0.0.1:8000`.

## API Reference

### Device Emulator Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/discover` | GET | Device discovery info |
| `/pair` | POST | Pair device |
| `/info` | GET | Device information |
| `/status` | GET | Current status |
| `/configure` | POST | Configure device |

### Backend Device Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/devices/discover` | GET | User | Scan for devices |
| `/devices/pair` | POST | Admin | Pair device |
| `/devices/registered` | GET | User | List devices |
| `/devices/{id}` | DELETE | Admin | Remove device |
| `/devices/{id}/status` | GET | User | Get status |

## Troubleshooting

### Devices Not Found
- Ensure devices are running (check console windows)
- Verify port range covers device ports
- Check Windows Firewall isn't blocking localhost

### Pairing Fails
- Verify you're logged in as admin
- Check device shows "Waiting for pairing"
- Ensure backend is running with HTTPS

### Events Not Received
- Verify device was configured with backend URL
- Check device console for send errors
- Ensure backend `/sensor` endpoint works
- Check SSL certificate trust

### Import Errors
- Install httpx: `pip install httpx`
- Activate virtual environment
- Reinstall requirements: `pip install -r backend/requirements.txt`

## Future Enhancements

1. **Enhanced Security:**
   - Implement payload encryption using shared secrets
   - Add device authentication tokens
   - Support certificate-based authentication

2. **Advanced Features:**
   - Device firmware updates
   - Remote configuration
   - Device groups and zones
   - Scheduling and automation rules
   - Device health monitoring
   - Battery level tracking

3. **Network Discovery:**
   - mDNS/Bonjour support
   - UPnP device discovery
   - Network topology mapping

4. **UI Improvements:**
   - Device setup wizard animations
   - Real-time device status updates via WebSocket
   - Device configuration dialogs
   - Bulk device operations

5. **Testing:**
   - Unit tests for discovery service
   - Integration tests for pairing flow
   - E2E tests for event processing
   - Load testing with many devices

## Contributing

When adding new device types:

1. Add type to `DeviceType` literal in `device.py`
2. Update `_get_initial_value()` for sensible defaults
3. Update `simulate_value_change()` for event generation
4. Add corresponding logic in `backend/logic.py`
5. Test pairing and event flow

## License

Part of the HP-SHSS project. See main project README for license information.
