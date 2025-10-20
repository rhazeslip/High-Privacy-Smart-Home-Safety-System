# Simulation/simulation.py
# Simple simulator that sends different sensor readings to the Edge Hub.

import time, random, requests

BASE = "http://127.0.0.1:8000"

def post(reading):
    try:
        r = requests.post(f"{BASE}/sensor", json=reading, timeout=3)
        print("->", reading, "| resp:", r.json())
    except Exception as e:
        print("POST failed:", e)

def simulate_once():
    # Door open/closed
    post({
        "sensor_id": "front_door_1",
        "type": "door",
        "value": random.choice(["open","closed"]),
        "location": "Front Door"
    })

    # Gas/CO (ppm)
    post({
        "sensor_id": "co_sensor_basement",
        "type": "co",
        "value": random.randint(40, 120),
        "location": "Basement"
    })

    # Water leak (0/1)
    post({
        "sensor_id": "water_heater_1",
        "type": "water",
        "value": random.choice([0,0,0,1]),   # mostly 0, sometimes 1
        "location": "Basement"
    })

    # Smoke (0~1)
    post({
        "sensor_id": "kitchen_smoke_1",
        "type": "smoke",
        "value": round(random.uniform(0.2, 0.9), 2),
        "location": "Kitchen"
    })

if __name__ == "__main__":
    while True:
        simulate_once()
        time.sleep(3)
