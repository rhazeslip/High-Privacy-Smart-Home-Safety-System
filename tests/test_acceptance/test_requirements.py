import pytest
from datetime import datetime

class TestAcceptanceCriteria:
    def test_alert_latency_requirement(self, test_client):
        start_time = datetime.now()

        test_client.post("/sensor", json={
            "sensor_id": "latency_test",
            "type": "smoke",
            "value": "0.8",
            "location": "Latency Test"
        })

        end_time = datetime.now()
        latency = (end_time - start_time).total_seconds()

        assert latency < 2.0, f"Alert latency {latency}s exceeds 2 second requirement"

    def test_sensor_capacity_requirement(self, test_client):
        from backend.store import SENSOR_LAST

        for i in range(10):
            test_client.post("/sensor", json={
                "sensor_id": f"capacity_test_{i}",
                "type": "door",
                "value": "closed",
                "location": f"Room {i}"
            })

        assert len(SENSOR_LAST) == 10
        assert len(SENSOR_LAST) <= 50

    def test_false_positive_rate(self, test_client):
        from backend.store import ALERTS

        normal_readings = [
            {"type": "gas", "value": 30},
            {"type": "smoke", "value": 0.3},
            {"type": "co", "value": 25},
            {"type": "water", "value": 0}
        ]
        for reading in normal_readings:
            test_client.post("/sensor", json={
                "sensor_id": "falsePositive_test",
                **reading,
                "location": "False Positive Test"
            })

        false_positives = [a for a in ALERTS if a.level == "critical"]
        false_positive_rate = len(false_positives) / len(normal_readings)

        assert false_positive_rate < 0.01, "False positive rate too high"