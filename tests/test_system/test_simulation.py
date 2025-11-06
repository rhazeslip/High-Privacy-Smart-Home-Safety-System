import pytest 
import time
from Simulation.simulation import SensorSimulator

class TestSimulationIntegration:
    def test_simulation_connection(self, test_client):
        simulator = SensorSimulator(base_url="http://testserver")
        
        simulator.simulate_normal_operation()

        status_response = test_client.get("/status")
        assert status_response.status_code == 200

        status_data = status_response.json()
        assert status_data["sensors_online"] > 0

    def test_emergency_scenario_alerts(self, test_client, auth_headers):
        simulator = SensorSimulator(base_url="http://testserver")

        simulator.simulate_emergency_scenario("fire")

        time.sleep(0.5)

        alerts_response = test_client.get("/alerts", headers=auth_headers)
        alerts = alerts_response.json()

        critical_alerts = [a for a in alerts if a["level"] == "critical"]
        assert len(critical_alerts) >= 1

    @pytest.mark.parametrize("scenario", ["fire", "gas_leak", "water_leak", "break_in"])
    def test_all_emergency_scenarios(self, test_client, scenario):
        simulator = SensorSimulator(base_url="http://testserver")

        from backend.store import ALERTS
        ALERTS.clear()

        simulator.simulate_emergency_scenario(scenario)

        time.sleep(0.5)
        
        assert len(ALERTS) >= 1, f"Scenario {scenario} should create alerts"