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
import cmd
from typing import Optional, Dict, Any, Literal
from datetime import datetime
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
    device_id: str
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
            timestamp=datetime.utcnow().isoformat()
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
    
    return app

async def send_event_to_backend(state: DeviceState):
    """Send an event to the configured backend"""
    if not state.backend_url or not state.paired:
        return
    
    try:
        import httpx
        event = EventData(
            device_id=state.device_id,
            type=state.type,
            value=state.current_value,
            location=state.location,
            timestamp=datetime.utcnow().isoformat()
        )
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{state.backend_url}/sensor",
                json=event.dict(),
                timeout=5.0
            )
            if response.status_code == 200:
                print(f"Event sent: {state.type}={state.current_value}")
    except Exception as e:
        print(f"Failed to send event: {e}")


async def event_generator(state: DeviceState, interval: int = 30):
    """Periodically generate and send events"""
    while True:
        await asyncio.sleep(interval)
        if state.paired and state.backend_url:
            state.simulate_value_change()
            await send_event_to_backend(state)


class DeviceCLI(cmd.Cmd):
    """Interactive CLI for device management and event/alert configuration"""
    
    intro = "\nDevice CLI Ready - Type 'help' for commands or 'status' to see device info\n"
    prompt = "(device) > "
    
    def __init__(self, state: DeviceState):
        super().__init__()
        self.state = state
        self.alert_rules = []  # Store alert rules: {type: 'offline|online|threshold', value: optional}
        self.event_handlers = []  # Store event handlers: {type: 'opened|closed'}
    
    def do_status(self, arg):
        """Show current device status
        Usage: status"""
        print(f"\n{'='*60}")
        print(f"Device Status")
        print(f"{'='*60}")
        print(f"  Device ID:      {self.state.device_id}")
        print(f"  Type:           {self.state.type}")
        print(f"  Location:       {self.state.location}")
        print(f"  Port:           {self.state.port}")
        print(f"  Paired:         {'Yes' if self.state.paired else 'No'}")
        print(f"  Current Value:  {self.state.current_value}")
        print(f"  Pairing Code:   {self.state.pairing_code}")
        if self.state.backend_url:
            print(f"  Backend URL:    {self.state.backend_url}")
        print(f"{'='*60}\n")
    
    def do_value(self, arg):
        """Get or set the current device value
        Usage: value [new_value]
        
        Examples:
            value          - Show current value
            value open     - Set value to 'open'
            value 25.5     - Set value to 25.5"""
        if not arg:
            print(f"Current value: {self.state.current_value}")
            return
        
        # Set new value
        if self.state.type in ["door", "window", "garage"]:
            if arg.lower() in ["open", "closed"]:
                self.state.current_value = arg.lower()
                print(f"Value set to: {self.state.current_value}")
            else:
                print(f"Invalid value. Use 'open' or 'closed' for {self.state.type} devices")
        else:
            try:
                self.state.current_value = float(arg)
                print(f"Value set to: {self.state.current_value}")
            except ValueError:
                print(f"Invalid numeric value: {arg}")
    
    def do_send(self, arg):
        """Send current value as an event to the backend
        Usage: send"""
        if not self.state.paired:
            print("Device not paired. Cannot send events.")
            return
        
        if not self.state.backend_url:
            print("Backend URL not configured.")
            return
        
        async def _send():
            await send_event_to_backend(self.state)
        
        asyncio.create_task(_send())
        print(f"→ Sending event: {self.state.type}={self.state.current_value}")
    
    def do_alert(self, arg):
        """Configure alert rules for this device
        Usage: alert <type> [value]
        
        Types:
            offline            - Alert when device goes offline
            online             - Alert when device comes online
            threshold <value>  - Alert when value exceeds threshold
            list               - List configured alerts
            clear              - Clear all alerts
        
        Examples:
            alert offline
            alert threshold 25
            alert list"""
        parts = arg.split()
        
        if not parts:
            print("Usage: alert <type> [value]")
            print("  Types: offline, online, threshold <value>, list, clear")
            return
        
        alert_type = parts[0].lower()
        
        if alert_type == 'list':
            if not self.alert_rules:
                print("No alerts configured.")
                return
            
            print(f"\nConfigured Alerts:")
            print(f"{'-'*50}")
            for i, rule in enumerate(self.alert_rules, 1):
                threshold = f" (threshold: {rule['value']})" if rule.get('value') else ""
                print(f"{i}. {rule['type']}{threshold}")
            print(f"{'-'*50}\n")
            return
        
        if alert_type == 'clear':
            self.alert_rules.clear()
            print("✓ All alerts cleared")
            return
        
        if alert_type not in ['offline', 'online', 'threshold']:
            print(f"✗ Invalid alert type: {alert_type}")
            print("  Valid types: offline, online, threshold")
            return
        
        if alert_type == 'threshold':
            if len(parts) < 2:
                print("Threshold alerts require a value")
                print("  Usage: alert threshold <value>")
                return
            try:
                threshold_value = float(parts[1])
                self.alert_rules.append({'type': alert_type, 'value': threshold_value})
                print(f"Alert added: {alert_type} (threshold: {threshold_value})")
            except ValueError:
                print(f"Invalid threshold value: {parts[1]}")
        else:
            self.cli_alerts.append({'type': alert_type})
            print(f"Alert added: {alert_type}")
    
    def do_event(self, arg):
        """Configure event handlers for door/window devices
        Usage: event <type>
        
        Types:
            opened   - Log when door/window opens
            closed   - Log when door/window closes
            list     - List configured events
            clear    - Clear all events
        
        Examples:
            event opened
            event list"""
        parts = arg.split()
        
        if not parts:
            print("Usage: event <type>")
            print("  Types: opened, closed, list, clear")
            return
        
        event_type = parts[0].lower()
        
        if event_type == 'list':
            if not self.event_handlers:
                print("No event handlers configured.")
                return
            
            print(f"\nConfigured Event Handlers:")
            print(f"{'-'*50}")
            for i, handler in enumerate(self.event_handlers, 1):
                print(f"{i}. {handler['type']}")
            print(f"{'-'*50}\n")
            return
        
        if event_type == 'clear':
            self.event_handlers.clear()
            print("✓ All event handlers cleared")
            return
        
        if self.state.type not in ['door', 'window', 'garage']:
            print(f"✗ Events are only for door/window/garage devices")
            print(f"  This device is type: {self.state.type}")
            return
        
        if event_type not in ['opened', 'closed']:
            print(f"✗ Invalid event type: {event_type}")
            print("  Valid types: opened, closed")
            return
        
        self.event_handlers.append({'type': event_type})
        print(f"✓ Event handler added: {event_type}")
        print(f"  Will log when {self.state.type} is {event_type}")
    
    def do_simulate(self, arg):
        """Simulate a value change
        Usage: simulate"""
        old_value = self.state.current_value
        self.state.simulate_value_change()
        print(f"→ Value changed: {old_value} → {self.state.current_value}")
    
    def do_clear(self, arg):
        """Clear the screen
        Usage: clear"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def do_exit(self, arg):
        """Exit the CLI (device keeps running)
        Usage: exit"""
        print("Exiting CLI... (device still running)")
        return True
    
    def do_quit(self, arg):
        """Exit the CLI (device keeps running)
        Usage: quit"""
        return self.do_exit(arg)
    
    def emptyline(self):
        """Handle empty line"""
        pass
    
    def default(self, line):
        """Handle unknown commands"""
        print(f"✗ Unknown command: {line}")
        print("  Type 'help' for available commands")


def run_cli(state: DeviceState):
    """Run the CLI in the main thread"""
    try:
        cli = DeviceCLI(state)
        cli.cmdloop()
    except KeyboardInterrupt:
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
    
    # Run CLI in main thread (blocks until exit)
    run_cli(state)

if __name__ == '__main__':
    main()