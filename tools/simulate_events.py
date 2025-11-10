#!/usr/bin/env python3
"""
Smart Home Event Simulator CLI
Simulate various events like sensor triggers, system state changes, and alerts.
"""

import argparse
import requests
import urllib3
import hashlib
import base64
import time
import random
import sys
from datetime import datetime

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://127.0.0.1:8000"

# Event templates
EVENT_TEMPLATES = {
    "fire": {
        "title": "Fire Detected",
        "message": "Smoke and high temperature detected",
        "level": "critical",
        "sensor_type": "smoke"
    },
    "gas_leak": {
        "title": "Gas Leak Detected",
        "message": "Dangerous gas levels detected",
        "level": "critical",
        "sensor_type": "gas"
    },
    "intrusion": {
        "title": "Intrusion Detected",
        "message": "Unauthorized entry detected",
        "level": "critical",
        "sensor_type": "motion"
    },
    "water_leak": {
        "title": "Water Leak Detected",
        "message": "Water detected in unusual location",
        "level": "warning",
        "sensor_type": "water"
    },
    "motion": {
        "title": "Motion Detected",
        "message": "Motion detected in monitored area",
        "level": "info",
        "sensor_type": "motion"
    },
    "door_open": {
        "title": "Door Opened",
        "message": "Door sensor triggered",
        "level": "info",
        "sensor_type": "door"
    },
    "window_open": {
        "title": "Window Opened",
        "message": "Window sensor triggered",
        "level": "info",
        "sensor_type": "window"
    },
    "temperature_high": {
        "title": "High Temperature Alert",
        "message": "Temperature exceeds safe threshold",
        "level": "warning",
        "sensor_type": "temperature"
    },
    "temperature_low": {
        "title": "Low Temperature Alert",
        "message": "Temperature below safe threshold",
        "level": "warning",
        "sensor_type": "temperature"
    },
    "power_outage": {
        "title": "Power Outage Detected",
        "message": "Backup power activated",
        "level": "warning",
        "sensor_type": "power"
    },
    "battery_low": {
        "title": "Low Battery Warning",
        "message": "Sensor battery level critical",
        "level": "warning",
        "sensor_type": "battery"
    },
    "network_down": {
        "title": "Network Connectivity Lost",
        "message": "Unable to reach monitoring server",
        "level": "warning",
        "sensor_type": "network"
    }
}

LOCATIONS = [
    "Living Room", "Kitchen", "Master Bedroom", "Bedroom 2", "Bedroom 3",
    "Bathroom", "Basement", "Garage", "Front Door", "Back Door",
    "Front Yard", "Backyard", "Hallway", "Attic", "Laundry Room"
]


def derive_client_hash(password: str, salt_b64: str) -> str:
    """Derive client-side password hash using PBKDF2."""
    salt = base64.b64decode(salt_b64)
    hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000, dklen=32)
    return hash_bytes.hex()


def login(username: str, password: str):
    """Login and get authentication token."""
    try:
        # Get salt
        response = requests.get(
            f"{BASE_URL}/auth/salt",
            params={"username": username},
            verify=False
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get salt: {response.status_code}")
            return None
        
        salt_b64 = response.json()["salt"]
        
        # Derive client hash
        client_hash = derive_client_hash(password, salt_b64)
        
        # Login
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": username, "client_hash": client_hash},
            verify=False
        )
        
        if response.status_code == 200:
            # Extract token from response JSON or cookie
            try:
                data = response.json()
                token = data.get('access_token')
                if token:
                    print(f"✅ Logged in as {username}")
                    return token
            except:
                pass
            
            # Try cookie
            cookies = response.cookies
            token = cookies.get('access_token')
            if token:
                print(f"✅ Logged in as {username}")
                return token
            
            print("❌ Login successful but no token received")
            return None
        else:
            print(f"❌ Login failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None


def create_alert(token: str, event_type: str, location: str = None, custom_message: str = None):
    """Create an alert based on event type."""
    if event_type not in EVENT_TEMPLATES:
        print(f"❌ Unknown event type: {event_type}")
        print(f"Available types: {', '.join(EVENT_TEMPLATES.keys())}")
        return False
    
    template = EVENT_TEMPLATES[event_type]
    
    # Random location if not provided
    if not location:
        location = random.choice(LOCATIONS)
    
    # Generate sensor ID
    sensor_id = f"{template['sensor_type']}_{location.lower().replace(' ', '_')}_{int(time.time())}"
    
    alert_data = {
        "title": template["title"],
        "message": custom_message or template["message"],
        "level": template["level"],
        "location": location,
        "sensor_id": sensor_id
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/alerts",
            json=alert_data,
            headers={"Authorization": f"Bearer {token}"},
            cookies={"access_token": token},
            verify=False
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Alert created: {template['title']} at {location}")
            print(f"   Level: {template['level']}")
            print(f"   Alert ID: {result.get('id', 'N/A')}")
            return True
        else:
            print(f"❌ Failed to create alert: {response.status_code}")
            if response.text:
                print(f"   {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating alert: {e}")
        return False


def simulate_scenario(token: str, scenario: str):
    """Simulate a predefined scenario with multiple events."""
    scenarios = {
        "break_in": [
            ("window_open", "Living Room"),
            ("motion", "Living Room"),
            ("motion", "Hallway"),
            ("intrusion", "Living Room")
        ],
        "fire_emergency": [
            ("temperature_high", "Kitchen"),
            ("fire", "Kitchen"),
            ("fire", "Living Room")
        ],
        "system_failure": [
            ("power_outage", "Main Panel"),
            ("battery_low", "Kitchen"),
            ("network_down", "Router")
        ],
        "water_damage": [
            ("water_leak", "Bathroom"),
            ("water_leak", "Hallway"),
            ("temperature_low", "Bathroom")
        ],
        "night_activity": [
            ("motion", "Hallway"),
            ("door_open", "Bedroom 2"),
            ("motion", "Kitchen"),
            ("motion", "Bathroom")
        ]
    }
    
    if scenario not in scenarios:
        print(f"❌ Unknown scenario: {scenario}")
        print(f"Available scenarios: {', '.join(scenarios.keys())}")
        return
    
    events = scenarios[scenario]
    print(f"🎬 Simulating scenario: {scenario}")
    print(f"   Events: {len(events)}")
    print()
    
    for i, (event_type, location) in enumerate(events, 1):
        print(f"[{i}/{len(events)}] ", end="")
        create_alert(token, event_type, location)
        if i < len(events):
            time.sleep(2)  # Delay between events
    
    print(f"\n✅ Scenario '{scenario}' completed!")


def list_events():
    """List all available event types."""
    print("\n📋 Available Event Types:\n")
    for event_type, template in EVENT_TEMPLATES.items():
        level_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
        emoji = level_emoji.get(template["level"], "⚪")
        print(f"  {emoji} {event_type:20s} - {template['title']}")
        print(f"     {template['message']}")
        print()


def list_scenarios():
    """List all available scenarios."""
    print("\n🎬 Available Scenarios:\n")
    scenarios = {
        "break_in": "Simulates a home intrusion with window breach and motion detection",
        "fire_emergency": "Simulates a fire starting in the kitchen and spreading",
        "system_failure": "Simulates system failures including power, battery, and network",
        "water_damage": "Simulates water leak spreading from bathroom",
        "night_activity": "Simulates normal nighttime movement in the house"
    }
    
    for scenario, description in scenarios.items():
        print(f"  🎬 {scenario:20s}")
        print(f"     {description}")
        print()


def random_events(token: str, count: int, delay: int = 3):
    """Generate random events."""
    print(f"🎲 Generating {count} random events with {delay}s delay...\n")
    
    event_types = list(EVENT_TEMPLATES.keys())
    
    for i in range(count):
        event_type = random.choice(event_types)
        location = random.choice(LOCATIONS)
        print(f"[{i+1}/{count}] ", end="")
        create_alert(token, event_type, location)
        
        if i < count - 1:
            time.sleep(delay)
    
    print(f"\n✅ Generated {count} random events!")


def main():
    parser = argparse.ArgumentParser(
        description="Smart Home Event Simulator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single event
  python simulate_events.py --event fire --location Kitchen
  
  # Multiple random events
  python simulate_events.py --random 10 --delay 2
  
  # Predefined scenario
  python simulate_events.py --scenario break_in
  
  # List available options
  python simulate_events.py --list-events
  python simulate_events.py --list-scenarios
        """
    )
    
    # Authentication
    parser.add_argument("-u", "--username", default="admin", help="Username (default: admin)")
    parser.add_argument("-p", "--password", default="admin123", help="Password (default: admin123)")
    
    # Event creation
    parser.add_argument("-e", "--event", help="Event type to simulate")
    parser.add_argument("-l", "--location", help="Location of event (random if not specified)")
    parser.add_argument("-m", "--message", help="Custom message for the event")
    
    # Bulk operations
    parser.add_argument("-r", "--random", type=int, metavar="COUNT", help="Generate COUNT random events")
    parser.add_argument("-d", "--delay", type=int, default=3, help="Delay between events in seconds (default: 3)")
    
    # Scenarios
    parser.add_argument("-s", "--scenario", help="Run predefined scenario")
    
    # Information
    parser.add_argument("--list-events", action="store_true", help="List all available event types")
    parser.add_argument("--list-scenarios", action="store_true", help="List all available scenarios")
    
    args = parser.parse_args()
    
    # Handle information requests
    if args.list_events:
        list_events()
        return
    
    if args.list_scenarios:
        list_scenarios()
        return
    
    # Require at least one action
    if not (args.event or args.random or args.scenario):
        parser.print_help()
        return
    
    # Login
    print(f"🔐 Logging in as {args.username}...")
    token = login(args.username, args.password)
    
    if not token:
        print("❌ Authentication failed. Cannot proceed.")
        sys.exit(1)
    
    print()
    
    # Execute requested action
    if args.scenario:
        simulate_scenario(token, args.scenario)
    elif args.random:
        random_events(token, args.random, args.delay)
    elif args.event:
        create_alert(token, args.event, args.location, args.message)


if __name__ == "__main__":
    main()
