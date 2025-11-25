"""
Device Discovery Module
Scans for emulated security devices on the local network
"""

import asyncio
import httpx
from typing import List, Dict, Any, Optional
import socket

async def check_device_at_port(port: int, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
    """
    Check if a device is running at the specified port
    Returns device info if found, None otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            url = f"http://127.0.0.1:{port}/discover"
            response = await client.get(url)
            if response.status_code == 200:
                device_info = response.json()
                device_info['port'] = port
                return device_info
    except (httpx.ConnectError, httpx.TimeoutException, httpx.ConnectTimeout):
        pass
    except Exception as e:
        # Silently ignore other errors during discovery
        pass
    return None

async def scan_ports(start_port: int = 8080, end_port: int = 8100, timeout: float = 0.5) -> List[Dict[str, Any]]:
    """
    Scan a range of ports for devices
    Returns list of discovered devices
    """
    tasks = []
    for port in range(start_port, end_port + 1):
        tasks.append(check_device_at_port(port, timeout))
    
    results = await asyncio.gather(*tasks)
    devices = [device for device in results if device is not None]
    return devices

async def discover_devices(start_port: int = 8080, count: int = 20, timeout: float = 0.5) -> List[Dict[str, Any]]:
    """
    Discover devices starting from start_port
    
    Args:
        start_port: First port to scan (default: 8080)
        count: Number of ports to scan (default: 20)
        timeout: Timeout for each port check in seconds (default: 0.5)
    
    Returns:
        List of discovered device information dictionaries
    """
    end_port = start_port + count - 1
    return await scan_ports(start_port, end_port, timeout)

async def get_device_status(port: int, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    """
    Get status from a specific device
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
            url = f"http://127.0.0.1:{port}/status"
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return None

async def pair_device(port: int, pairing_code: Optional[str] = None, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    """
    Pair with a device at the specified port
    
    Args:
        port: Port where device is running
        pairing_code: Optional pairing code (6-digit string)
        timeout: Request timeout in seconds
    
    Returns:
        Pairing response with shared secret if successful
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            url = f"http://127.0.0.1:{port}/pair"
            payload = {}
            if pairing_code:
                payload['pairing_code'] = pairing_code
            
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"Error pairing with device on port {port}: {e}")
    return None

async def configure_device(port: int, backend_url: str, timeout: float = 2.0) -> bool:
    """
    Configure a device with the backend URL for event sending
    
    Args:
        port: Port where device is running
        backend_url: Backend URL (e.g., https://localhost:8000)
        timeout: Request timeout in seconds
    
    Returns:
        True if successful, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
            url = f"http://127.0.0.1:{port}/configure"
            payload = {"backend_url": backend_url}
            
            response = await client.post(url, json=payload)
            return response.status_code == 200
    except Exception as e:
        print(f"Error configuring device on port {port}: {e}")
        return False
