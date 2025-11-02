# Simulation/simulation.py
# Sensor simulator for HP-SHSS. Sends normal & emergency readings to the Edge Hub API.

import time
import random
import requests
from datetime import datetime
import argparse


class SensorSimulator:
    # Base URL is configurable; set insecure=True to skip TLS verify for self-signed certs.
    def __init__(self, base_url: str = "http://localhost:8000", insecure: bool = False):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.verify = not insecure  # EN: False allows self-signed HTTPS during local dev

        # Canonical sensor definitions (IDs and types must match backend expectations).
        self.sensors = {
            "entry_sensors": [
                {"id": "front_door_1",     "type": "door",   "location": "Front Door"},
                {"id": "back_door_1",      "type": "door",   "location": "Kitchen"},
                {"id": "garage_door_1",    "type": "door",   "location": "Garage"},
                {"id": "kitchen_window_1", "type": "window", "location": "Kitchen Window"},
            ],
            "environmental_sensors": [
                {"id": "co_kitchen_1",     "type": "co",     "location": "Kitchen"},
                {"id": "gas_basement_1",   "type": "gas",    "location": "Basement"},
                {"id": "water_heater_1",   "type": "water",  "location": "Basement"},
                {"id": "smoke_kitchen_1",  "type": "smoke",  "location": "Kitchen"},
            ],
        }

    # Send a single sensor reading to the backend API.
    def _send_sensor_data(self, sensor_id: str, sensor_type: str, value, location: str):
        data = {
            "sensor_id": sensor_id,
            "type": sensor_type,
            "value": value,
            "location": location,
            "ts": datetime.utcnow().isoformat()
        }
        try:
            resp = self.session.post(f"{self.base_url}/sensor", json=data, timeout=5)
            if resp.status_code == 200:
                result = resp.json()
                if result.get("alerts_created", 0) > 0:
                    print(f"[ALERT] {sensor_id} -> {value} ({sensor_type})")
                else:
                    print(f"[OK] {sensor_id} -> {value} ({sensor_type})")
            else:
                print(f"[FAIL] {sensor_id} status={resp.status_code} body={resp.text[:120]}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] {sensor_id}: {e}")

    # Simulate normal background readings (mostly safe values).
    def simulate_normal_operation(self):
        print("Simulating normal operation...")
        # Doors/windows: mostly closed, sometimes open
        for s in self.sensors["entry_sensors"]:
            value = "closed" if random.random() > 0.1 else "open"
            self._send_sensor_data(s["id"], s["type"], value, s["location"])

        # CO/Gas/Water/Smoke: normal ranges
        self._send_sensor_data("co_kitchen_1",    "co",    random.randint(5, 30),            "Kitchen")
        self._send_sensor_data("gas_basement_1",  "gas",   random.randint(0, 20),            "Basement")
        self._send_sensor_data("water_heater_1",  "water", 0,                                 "Basement")
        self._send_sensor_data("smoke_kitchen_1", "smoke", round(random.uniform(0.1, 0.3), 2), "Kitchen")

    # Simulate emergency scenarios that should trigger alerts.
    def simulate_emergency_scenario(self, scenario_type: str):
        print(f"Simulating {scenario_type} emergency...")

        if scenario_type == "fire":
            self._send_sensor_data("smoke_kitchen_1", "smoke", 0.85, "Kitchen")
            self._send_sensor_data("co_kitchen_1",    "co",    45,   "Kitchen")

        elif scenario_type == "gas_leak":
            self._send_sensor_data("gas_basement_1",  "gas",   150,  "Basement")
            self._send_sensor_data("co_kitchen_1",    "co",    85,   "Kitchen")

        elif scenario_type == "water_leak":
            self._send_sensor_data("water_heater_1",  "water", 1,    "Basement")
            self._send_sensor_data("front_door_1",    "door",  "open","Front Door")

        elif scenario_type == "break_in":
            self._send_sensor_data("front_door_1",     "door",   "open",  "Front Door")
            self._send_sensor_data("kitchen_window_1", "window", "open",  "Kitchen Window")

        else:
            print(f"[WARN] Unknown scenario: {scenario_type}")

    # Loop with mostly normal traffic and occasional emergencies.
    def run_continuous_simulation(self, interval: int = 5):
        scenario_count = 0
        while True:
            if random.random() > 0.2:
                self.simulate_normal_operation()
            else:
                scenario = random.choice(["fire", "gas_leak", "water_leak", "break_in"])
                self.simulate_emergency_scenario(scenario)
                scenario_count += 1
                print(f"[INFO] Emergency scenarios triggered so far: {scenario_count}")
            print("---")
            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="HP-SHSS Sensor Simulator")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Backend API base URL, e.g., http://127.0.0.1:8000 or https://127.0.0.1:8443",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Simulation interval in seconds (for continuous mode)",
    )
    parser.add_argument(
        "--scenario",
        choices=["fire", "gas_leak", "water_leak", "break_in", "continuous"],
        default="continuous",
        help="Specific scenario to run or continuous mixed simulation",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Skip TLS verification (useful for HTTPS with self-signed certs in local dev)",
    )

    args = parser.parse_args()
    sim = SensorSimulator(base_url=args.base_url, insecure=args.insecure)

    if args.scenario == "continuous":
        print("Starting continuous simulation...")
        sim.run_continuous_simulation(interval=args.interval)
    else:
        print(f"Running {args.scenario} scenario...")
        sim.simulate_emergency_scenario(args.scenario)
        time.sleep(2)


if __name__ == "__main__":
    main()
