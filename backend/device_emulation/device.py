"""
Emulated Security Device
A simulated smart home security device that can be discovered and controlled by the backend.
Supports:
- Device discovery (responds to discovery pings)
- Status queries
- Event generation and sending
- End-to-end encryption using shared secrets
"""

import uvicorn
import socket
import secrets
import hashlib
import json
import time
import random
import asyncio
import threading
from typing import Optional, Dict, Any, Literal
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import argparse
import sys
import os

# Device types that can be emulated
DeviceType = Literal["door", "window", "garage", "gas", "co", "water", "fire", "smoke", "temp"]

class DeviceInfo(BaseModel):
    """Information about this device"""
    device_id: str
    name: str
    type: DeviceType
    location: str
    firmware_version: str = "1.0.0"
    model: str = "EMULATED-DEVICE"

class DeviceStatus(BaseModel):
    """Current status of the device"""
    device_id: str
    type: DeviceType
    value: float | str
    location: str
    online: bool = True
    battery: int = 100
    signal_strength: int = 100
    timestamp: str

class EventData(BaseModel):
    """Event sent from device to backend"""
    sensor_id: str  # Changed from device_id to match backend SensorReading model
    type: DeviceType
    value: float | str
    location: str
    timestamp: str
    event_type: str = "reading"

class PairingRequest(BaseModel):
    """Request to pair with this device"""
    pairing_code: Optional[str] = None

class PairingResponse(BaseModel):
    """Response to pairing request"""
    success: bool
    device_id: str
    shared_secret: Optional[str] = None
    message: str

# Global state for this emulated device
class DeviceState:
    def __init__(self, device_id: str, device_type: DeviceType, location: str, port: int):
        self.device_id = device_id
        self.type = device_type
        self.location = location
        self.port = port
        self.paired = False
        self.shared_secret: Optional[str] = None
        self.pairing_code = self._generate_pairing_code()
        self.backend_url: Optional[str] = None
        self.current_value = self._get_initial_value()
        self.battery = 100
        self.event_task: Optional[asyncio.Task] = None
        
    def _generate_pairing_code(self) -> str:
        """Generate a 6-digit pairing code"""
        return str(random.randint(100000, 999999))
    
    def _get_initial_value(self):
        """Get initial value based on device type"""
        if self.type in ["door", "window", "garage"]:
            return "closed"
        elif self.type in ["gas", "co"]:
            return 0.0
        elif self.type == "water":
            return 0
        elif self.type in ["smoke", "fire"]:
            return 0.0
        elif self.type == "temp":
            return 20.0
        return 0
    
    def simulate_value_change(self):
        """Simulate a value change for event generation"""
        if self.type in ["door", "window", "garage"]:
            # Toggle between open/closed
            self.current_value = "open" if self.current_value == "closed" else "closed"
        elif self.type in ["gas", "co"]:
            # Occasionally spike, usually low
            if random.random() < 0.1:
                self.current_value = round(random.uniform(50, 200), 2)
            else:
                self.current_value = round(random.uniform(0, 5), 2)
        elif self.type == "water":
            # Occasionally detect water
            self.current_value = 1 if random.random() < 0.05 else 0
        elif self.type in ["smoke", "fire"]:
            # Occasionally spike
            if random.random() < 0.05:
                self.current_value = round(random.uniform(0.5, 1.0), 2)
            else:
                self.current_value = round(random.uniform(0, 0.1), 2)
        elif self.type == "temp":
            # Gradual temperature changes
            self.current_value = round(self.current_value + random.uniform(-1, 1), 1)

def check_port(host: str, port: int, timeout: float = 2) -> bool:
    """Check if a port is already in use"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
    except:
        return False
    else:
        sock.close()
        return True

def create_device_app(state: DeviceState) -> FastAPI:
    """Create FastAPI app for the emulated device"""
    app = FastAPI(title=f"Emulated {state.type.capitalize()} Sensor", version="1.0.0")
    
    @app.get("/")
    async def root():
        """Basic endpoint to confirm device is online"""
        return {"status": "online", "device_id": state.device_id}
    
    @app.get("/discover")
    async def discover():
        """Discovery endpoint - returns basic device info without requiring pairing"""
        return {
            "device_id": state.device_id,
            "type": state.type,
            "location": state.location,
            "model": "HP-SHSS-SIM",
            "firmware_version": "1.0.0",
            "requires_pairing": not state.paired,
            "port": state.port
        }
    
    @app.post("/pair")
    async def pair(request: PairingRequest):
        """Pair with this device using the pairing code"""
        if state.paired:
            return PairingResponse(
                success=False,
                device_id=state.device_id,
                message="Device already paired"
            )
        
        # For simulation, we accept any pairing code or auto-pair
        # In production, would verify the pairing code matches
        if request.pairing_code is None or request.pairing_code == state.pairing_code:
            # Generate shared secret for encryption
            state.shared_secret = secrets.token_urlsafe(32)
            state.paired = True
            
            print(f"Device {state.device_id} paired successfully!")
            print(f"  Shared secret: {state.shared_secret[:16]}...")
            
            return PairingResponse(
                success=True,
                device_id=state.device_id,
                shared_secret=state.shared_secret,
                message="Pairing successful"
            )
        else:
            return PairingResponse(
                success=False,
                device_id=state.device_id,
                message="Invalid pairing code"
            )
    
    @app.get("/info")
    async def get_info():
        """Get device information"""
        return DeviceInfo(
            device_id=state.device_id,
            name=f"{state.type.capitalize()} - {state.location}",
            type=state.type,
            location=state.location
        )
    
    @app.get("/status")
    async def get_status(authorization: Optional[str] = Header(None)):
        """Get current device status - requires pairing for encrypted response"""
        if not state.paired:
            raise HTTPException(status_code=403, detail="Device not paired")
        
        status = DeviceStatus(
            device_id=state.device_id,
            type=state.type,
            value=state.current_value,
            location=state.location,
            battery=state.battery,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        return status
    
    @app.post("/configure")
    async def configure(config: Dict[str, Any], authorization: Optional[str] = Header(None)):
        """Configure device settings"""
        if not state.paired:
            raise HTTPException(status_code=403, detail="Device not paired")
        
        # Update backend URL if provided
        if "backend_url" in config:
            state.backend_url = config["backend_url"]
            print(f"Backend URL configured: {state.backend_url}")
        
        return {"success": True, "message": "Configuration updated"}
    
    @app.post("/unpair")
    async def unpair():
        """Handle unpair notification from backend"""
        if state.paired:
            state.paired = False
            state.shared_secret = None
            state.backend_url = None
            print(f"\n[!] Device {state.device_id} has been unpaired by backend")
            print(f"[!] New pairing code: {state.pairing_code}\n")
        
        return {"success": True, "message": "Device unpaired"}
    
    return app

async def send_event_to_backend(state: DeviceState):
    """Send an event to the configured backend"""
    if not state.backend_url or not state.paired:
        return
    
    try:
        import httpx
        event = EventData(
            sensor_id=state.device_id,  # Use device_id as sensor_id
            type=state.type,
            value=state.current_value,
            location=state.location,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{state.backend_url}/sensor",
                json=event.model_dump(),
                timeout=5.0
            )
            if response.status_code == 200:
                print(f"Event sent: {state.type}={state.current_value}")
                return True
    except Exception as e:
        print(f"Failed to send event: {e}")
    return False


def send_event_sync(state: DeviceState):
    """Synchronous wrapper to send event from non-async context"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_event_to_backend(state))
        loop.close()
    except Exception as e:
        print(f"Failed to send event: {e}")


async def event_generator(state: DeviceState, interval: int = 30):
    """Periodically generate and send events"""
    while True:
        await asyncio.sleep(interval)
        if state.paired and state.backend_url:
            state.simulate_value_change()
            await send_event_to_backend(state)


def run_simple_ui(state: DeviceState):
    """Run simple prompt-based UI in terminal"""
    
    def clear_screen():
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_menu():
        print(f"{'='*40}")
        print(f"  Device: {state.device_id} ({state.type}) - Port {state.port}")
        print(f"  Location: {state.location}")
        print(f"  Pairing Code: {state.pairing_code}")
        print(f"  Battery: {state.battery}%")
        print(f"  Paired: {'Yes' if state.paired else 'No'}")
        print(f"  Current Value: {state.current_value}")
        print(f"{'='*60}")
        print("\n  [1] Set Battery Level")
        print("  [2] Change State")
        print("  [3] Send Event")
        print("  [0] Shutdown")
        print(f"{'='*40}\n")
    
    clear_screen()
    print("\nDevice Emulation")
    print(f"Device {state.device_id} running on port {state.port}\n")
    
    while True:
        try:
            show_menu()
            choice = input("Select option: ").strip()
            
            if choice == '1':
                try:
                    new_battery = int(input("Enter battery percentage (0-100): ").strip())
                    if 0 <= new_battery <= 100:
                        state.battery = new_battery
                        print(f"✓ Battery set to {state.battery}%")
                        # Send update to backend if paired
                        if state.paired and state.backend_url:
                            send_event_sync(state)
                    else:
                        print("✗ Battery must be between 0 and 100")
                except ValueError:
                    print("✗ Invalid number")
                input("\nPress Enter to continue...")
                
            elif choice == '2':
                if state.type in ["door", "window", "garage"]:
                    print("Options: open, closed")
                    new_value = input("Enter value: ").strip().lower()
                    if new_value in ["open", "closed"]:
                        state.current_value = new_value
                        print(f"✓ Value set to: {state.current_value}")
                        # Send update to backend if paired
                        if state.paired and state.backend_url:
                            send_event_sync(state)
                    else:
                        print("✗ Invalid value. Use 'open' or 'closed'")
                else:
                    try:
                        new_value = float(input(f"Enter {state.type} value: ").strip())
                        state.current_value = new_value
                        print(f"✓ Value set to: {state.current_value}")
                        # Send update to backend if paired
                        if state.paired and state.backend_url:
                            send_event_sync(state)
                    except ValueError:
                        print("✗ Invalid number")
                input("\nPress Enter to continue...")
                
            elif choice == '3':
                if not state.paired:
                    print("✗ Device not paired. Cannot send events.")
                elif not state.backend_url:
                    print("✗ Backend URL not configured.")
                else:
                    print(f"✓ Sending event: {state.type}={state.current_value}")
                    asyncio.run(send_event_to_backend(state))
                input("\nPress Enter to continue...")
                
            elif choice == '0':
                print("\nShutting down device server...")
                sys.exit(0)
                
            else:
                print("✗ Invalid option")
                input("\nPress Enter to continue...")
                
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            sys.exit(0)
        except EOFError:
            print("\n\nShutting down...")
            sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Emulated Security Device")
    parser.add_argument("--port", type=int, default=None, help="Port to run on (auto-detect if not specified)")
    parser.add_argument("--type", type=str, default="door", choices=["door", "window", "garage", "gas", "co", "water", "fire", "smoke", "temp"], help="Device type")
    parser.add_argument("--location", type=str, default="Unknown", help="Device location")
    parser.add_argument("--name", type=str, default=None, help="Device name")
    parser.add_argument("--auto-events", action="store_true", help="Automatically send events every 30s")
    parser.add_argument("--event-interval", type=int, default=30, help="Event interval in seconds")
    
    args = parser.parse_args()
    
    # Auto-detect available port starting from 8080
    if args.port is None:
        port = 8080
        while check_port('127.0.0.1', port, timeout=0.5):
            port += 1
    else:
        port = args.port
    
    # Generate device ID
    device_id = f"{args.type}_{port}"
    
    # Create device state
    state = DeviceState(
        device_id=device_id,
        device_type=args.type,
        location=args.location,
        port=port
    )
    
    # Create FastAPI app
    app = create_device_app(state)
    
    # Print device info
    print("\n" + "="*60)
    print(f"🔒 HP-SHSS Emulated Security Device")
    print("="*60)
    print(f"Device ID:      {state.device_id}")
    print(f"Type:           {state.type}")
    print(f"Location:       {state.location}")
    print(f"Port:           {port}")
    print(f"Pairing Code:   {state.pairing_code}")
    print(f"Discovery URL:  http://127.0.0.1:{port}/discover")
    print("="*60)
    print(f"Status:         Waiting for pairing...")
    print("="*60 + "\n")
    
    # Start event generator if requested
    if args.auto_events:
        @app.on_event("startup")
        async def startup_event():
            state.event_task = asyncio.create_task(event_generator(state, args.event_interval))
        
        @app.on_event("shutdown")
        async def shutdown_event():
            if state.event_task:
                state.event_task.cancel()
    
    # Run the device server in a background thread
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Give server a moment to start
    time.sleep(1)
    
    # Run simple UI in main thread (blocks until exit)
    run_simple_ui(state)

if __name__ == '__main__':
    main()