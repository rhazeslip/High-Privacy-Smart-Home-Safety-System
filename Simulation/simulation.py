# Simulation/simulation.py
# Simple simulator that sends different sensor readings to the Edge Hub.

import time
import random
import requests
import json
from datetime import datetime

BASE = "http://127.0.0.1:8000"

class SensorSimulator:
    def __init__(self, url_base="http://localhost:8000"):
        self.url_base = url_base
        self.sensors = {
            "entry_sensors": [
                {"id": "front_door_1", "type": "door", "location": "Front Door"},
                {"id": "back_door_1", "type": "door", "location": "Kitchen"},
                {"id": "garage_door_1", "type": "door", "location": "Garage"},
                {"id": "kitchen_window_1", "type": "door", "location": "Kitchen Window"}
            ],
            "environmental_sensors": [
                {"id": "co_kitchen_1", "type": "co", "location": "Kitchen"},
                {"id": "gas_basement_1", "type": "gas", "location": "Basement"},
                {"id": "water_heater_1", "type": "water", "location": "Basement"},
                {"id": "kitchen_smoke_1", "type": "smoke", "location": "Kitchen"}
            ]
        }
        

    def simulate_emergency_scenario(self, scenario_type):
        #Simulate specific emergency scenarios
        print(f"Simulating {scenario_type} emergency...")
        
        if scenario_type == "fire":
            self._send_sensor_data("smoke_kitchen_1", "smoke", 0.85, "Kitchen") 
            self._send_sensor_data("co_kitchen_1", "co", 45, "Kitchen") 
            
        elif scenario_type == "gas_leak":
            self._send_sensor_data("gas_basement_1", "gas", 150, "Basement")  
            self._send_sensor_data("co_kitchen_1", "co", 85, "Kitchen")  
            
        elif scenario_type == "water_leak":
            self._send_sensor_data("water_heater_1", "water", 1, "Basement")  
            self._send_sensor_data("front_door_1", "door", "open", "Front Door")  
            
        elif scenario_type == "break_in":
            self._send_sensor_data("front_door_1", "door", "open", "Front Door")
            self._send_sensor_data("kitchen_window_1", "window", "open", "Kitchen")

    def simulate_normal_operation(self):
        #Normal Sensor Readings
        print("Simulating normal operation...")
        
        for sensor in self.sensors["entry_sensors"]:
            value = "closed" if random.random() > 0.1 else "open"
            self._send_sensor_data(sensor["id"], sensor["type"], value, sensor["location"])
        
        self._send_sensor_data("co_kitchen_1", "co", random.randint(5, 30), "Kitchen")
        self._send_sensor_data("gas_basement_1", "gas", random.randint(0, 20), "Basement")
        self._send_sensor_data("water_heater_1", "water", 0, "Basement")  # No water
        self._send_sensor_data("smoke_kitchen_1", "smoke", round(random.uniform(0.1, 0.3), 2), "Kitchen")

    def _send_sensor_data(self, sensor_id, sensor_type, value, location):
        #Send sensor data to backend API
        data = {
            "sensor_id": sensor_id,
            "type": sensor_type,
            "value": value,
            "location": location,
            "ts": datetime.utcnow().isoformat()
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/sensor",
                json=data,
                timeout=5
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("alerts_created", 0) > 0:
                    print(f"ALERT TRIGGERED: {sensor_id} = {value}")
                else:
                    print(f"Sensor data sent: {sensor_id} = {value}")
            else:
                print(f"Failed to send {sensor_id}: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"Connection error for {sensor_id}: {e}")

    def run_continuous_simulation(self, interval=5):
        #Continuous simulation with occasional emergencies
        scenario_count = 0
        
        while True:
            if random.random() > 0.2:
                self.simulate_normal_operation()
            else:
                scenarios = ["fire", "gas_leak", "water_leak", "break_in"]
                scenario = random.choice(scenarios)
                self.simulate_emergency_scenario(scenario)
                scenario_count += 1
                print(f"🎭 Emergency scenarios triggered: {scenario_count}")
            
            print("---")  
            time.sleep(interval)

#Command-line interface to run simulations
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='HP-SHSS Sensor Simulator')
    parser.add_argument('--base-url', default='http://localhost:8000', 
                       help='Backend API base URL')
    parser.add_argument('--interval', type=int, default=5, 
                       help='Simulation interval in seconds')
    parser.add_argument('--scenario', choices=['fire', 'gas_leak', 'water_leak', 'break_in', 'continuous'],
                       default='continuous', help='Specific scenario to run')
    
    args = parser.parse_args()
    
    simulator = SensorSimulator(base_url=args.base_url)
    
    if args.scenario == 'continuous':
        print("Starting continuous simulation...")
        simulator.run_continuous_simulation(interval=args.interval)
    else:
        print(f"Running {args.scenario} scenario...")
        simulator.simulate_emergency_scenario(args.scenario)
        time.sleep(2)
