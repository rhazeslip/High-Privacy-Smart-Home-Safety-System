import pytest
from backend.models import SensorReading

class TestAPIEndpoints:
    def test_status_endpoint(self, test_client):
        response = test_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["system"] == "running"
        assert "sensors_online" in data
        assert "alerts_open" in data

    def test_sensor_data_ingestion(self, test_client):
        sensor_data = {
            "sensor_id": "component_test_sensor",
            "type": "door",
            "value": "open",
            "location": "component Test Room"
        }

        response = test_client.post("/sensor", json=sensor_data)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert "alerts_created" in data
        assert "alert_ids" in data

    def test_alerts_endpoint(self, test_client, auth_headers):
        test_client.post("/sensor", json={
            "sensor_id": "alert_test",
            "type": "door",
            "value": "open",
            "location": "Alert Test Room"
        })
        response = test_client.get("/alerts", headers=auth_headers)

        assert response.status_code == 200
        alerts = response.json()
        assert isinstance(alerts, list)

    def test_alert_acknowledgment(self, test_client, auth_headers):
        sensor_response = test_client.post("/sensor", json ={
            "sensor_id": "ack_test",
            "type": "door",
            "value": "open",
            "location": "Ack Test Room"
        })
        alert_id = sensor_response.json()["alert_ids"][0]

        ack_response = test_client.post(f"/alerts/{alert_id}/ack",
                                        headers=auth_headers)
        assert ack_response.status_code == 200
        assert ack_response.json()["ok"] == True