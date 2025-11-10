#!/usr/bin/env python3
"""
Alert Trigger Script for High-Privacy Smart Home Safety System

This script allows you to manually trigger alerts for testing purposes.
It sends authenticated requests to the backend API to create alerts.

Usage:
    python trigger_alert.py --type fire --severity critical
    python trigger_alert.py --type gas_leak --severity warning --message "Gas detected in kitchen"
    python trigger_alert.py --username admin --password admin123 --type intrusion
"""

import argparse
import requests
import urllib3
import hashlib
import base64
from datetime import datetime

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Alert types
ALERT_TYPES = [
    'fire',
    'gas_leak',
    'water_leak',
    'intrusion',
    'motion',
    'smoke',
    'co_detected',
    'door_open',
    'window_open',
    'temperature_high',
    'temperature_low',
    'power_outage',
    'system_error',
    'sensor_offline'
]

# Severity levels
SEVERITY_LEVELS = ['critical', 'warning', 'info']

# Default messages for each alert type
DEFAULT_MESSAGES = {
    'fire': 'Fire detected! Evacuate immediately!',
    'gas_leak': 'Gas leak detected. Ventilate area immediately.',
    'water_leak': 'Water leak detected. Check plumbing.',
    'intrusion': 'Unauthorized entry detected!',
    'motion': 'Motion detected in restricted area.',
    'smoke': 'Smoke detected. Check for fire hazards.',
    'co_detected': 'Carbon monoxide detected! Ventilate immediately!',
    'door_open': 'Door opened unexpectedly.',
    'window_open': 'Window opened unexpectedly.',
    'temperature_high': 'Temperature above safe threshold.',
    'temperature_low': 'Temperature below safe threshold.',
    'power_outage': 'Power outage detected. Running on backup.',
    'system_error': 'System malfunction detected.',
    'sensor_offline': 'Sensor connection lost.'
}

# Default locations for each alert type
DEFAULT_LOCATIONS = {
    'fire': 'Living Room',
    'gas_leak': 'Kitchen',
    'water_leak': 'Bathroom',
    'intrusion': 'Front Door',
    'motion': 'Hallway',
    'smoke': 'Bedroom',
    'co_detected': 'Garage',
    'door_open': 'Front Door',
    'window_open': 'Bedroom Window',
    'temperature_high': 'Attic',
    'temperature_low': 'Basement',
    'power_outage': 'Main Panel',
    'system_error': 'Control Hub',
    'sensor_offline': 'Back Porch'
}


def login(base_url, username, password):
    """Authenticate and get access token."""
    print(f"Logging in as {username}...")
    
    # First, get the salt
    salt_response = requests.get(
        f'{base_url}/auth/salt',
        params={'username': username},
        verify=False
    )
    
    if salt_response.status_code != 200:
        print(f"Error getting salt: {salt_response.text}")
        return None
    
    salt_data = salt_response.json()
    salt_base64 = salt_data.get('salt')
    
    if not salt_base64:
        print("Error: No salt returned from server")
        return None
    
    # Decode the base64 salt
    salt = base64.b64decode(salt_base64)
    
    # Derive client_hash using PBKDF2 (matching frontend implementation)
    client_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000,  # 100k iterations
        dklen=32  # 32 bytes output
    )
    # Convert to hex string (matching frontend)
    client_hash_hex = client_hash.hex()
    
    print(f"Derived client hash for authentication")
    
    # Login with client_hash
    login_response = requests.post(
        f'{base_url}/auth/login',
        json={'username': username, 'client_hash': client_hash_hex},
        verify=False
    )
    
    if login_response.status_code == 200:
        print("Login successful!")
        # Extract cookies
        return login_response.cookies
    else:
        print(f"Login failed: {login_response.status_code} - {login_response.text}")
        return None


def create_alert(base_url, cookies, alert_type, severity, message=None, location=None):
    """Create an alert via the API."""
    
    # Use default message if not provided
    if message is None:
        message = DEFAULT_MESSAGES.get(alert_type, f'{alert_type} detected')
    
    # Use default location if not provided
    if location is None:
        location = DEFAULT_LOCATIONS.get(alert_type, 'Unknown Location')
    
    # Generate title from alert type
    title = alert_type.replace('_', ' ').title()
    
    alert_data = {
        'title': title,
        'message': message,
        'level': severity,
        'sensor_id': f'sensor_{alert_type}_{location.lower().replace(" ", "_")}',
        'location': location,
        'acknowledged': False
    }
    
    print(f"\nCreating alert:")
    print(f"  Type: {alert_type}")
    print(f"  Severity: {severity}")
    print(f"  Location: {location}")
    print(f"  Message: {message}")
    
    response = requests.post(
        f'{base_url}/alerts',
        json=alert_data,
        cookies=cookies,
        verify=False
    )
    
    if response.status_code == 200 or response.status_code == 201:
        print("✓ Alert created successfully!")
        return True
    else:
        print(f"✗ Failed to create alert: {response.status_code} - {response.text}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Trigger alerts in the Smart Home Safety System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Trigger a critical fire alert
  python trigger_alert.py --type fire --severity critical
  
  # Trigger a warning with custom message
  python trigger_alert.py --type gas_leak --severity warning --message "Gas detected in kitchen"
  
  # Trigger multiple alerts
  python trigger_alert.py --type fire --severity critical
  python trigger_alert.py --type intrusion --severity critical
  python trigger_alert.py --type water_leak --severity warning
  
  # Use custom credentials
  python trigger_alert.py --username alice --password alice123 --type motion --severity info
        '''
    )
    
    parser.add_argument(
        '--base-url',
        default='https://localhost:8000',
        help='Base URL of the backend API (default: https://localhost:8000)'
    )
    
    parser.add_argument(
        '--username',
        default='admin',
        help='Username for authentication (default: admin)'
    )
    
    parser.add_argument(
        '--password',
        default='admin123',
        help='Password for authentication (default: admin123)'
    )
    
    parser.add_argument(
        '--type',
        required=True,
        choices=ALERT_TYPES,
        help='Type of alert to trigger'
    )
    
    parser.add_argument(
        '--severity',
        default='warning',
        choices=SEVERITY_LEVELS,
        help='Severity level of the alert (default: warning)'
    )
    
    parser.add_argument(
        '--message',
        help='Custom alert message (default: auto-generated based on type)'
    )
    
    parser.add_argument(
        '--location',
        help='Location where the alert occurred (default: auto-generated based on type)'
    )
    
    parser.add_argument(
        '--count',
        type=int,
        default=1,
        help='Number of alerts to create (default: 1)'
    )
    
    args = parser.parse_args()
    
    # Login
    cookies = login(args.base_url, args.username, args.password)
    if not cookies:
        print("Authentication failed. Exiting.")
        return 1
    
    # Create alert(s)
    success_count = 0
    for i in range(args.count):
        if args.count > 1:
            print(f"\n--- Alert {i+1}/{args.count} ---")
        
        if create_alert(
            args.base_url,
            cookies,
            args.type,
            args.severity,
            args.message,
            args.location
        ):
            success_count += 1
    
    print(f"\n{'='*50}")
    print(f"Created {success_count}/{args.count} alert(s)")
    print(f"{'='*50}")
    
    return 0 if success_count == args.count else 1


if __name__ == '__main__':
    exit(main())
