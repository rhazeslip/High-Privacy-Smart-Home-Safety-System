import pytest
from backend.models import SensorReading
from backend.logic import process_reading
from backend.store import ALERTS

class TestAlertLogic:
    def test_door_open_creats_alert(self):
        reading = SensorReading(
            sensor_id="test_door",
            type="door",
            value="open",
            location="Test Room"
        )

        alerts = process_reading(reading)

        assert len(alerts) == 1
        assert alerts[0].level == "warning"
        assert "Entry Open" in alerts[0].title
        assert len(ALERTS) == 1

    def test_door_closed_no_alert(self):
        reading = SensorReading(
            sensor_id="test_door",
            type="door",
            value="closed",
            location="Test Room"
        )

        alerts = process_reading(reading)
        assert len(alerts) == 0

    def test_gas_leak_creates_critical_alert(self):
        reading = SensorReading(
            sensor_id="test_gas",
            type="gas",
            value="85.0", #Threshold 70.0 ppm
            location="Basement"
        )

        alerts = process_reading(reading)
        assert len(alerts) == 1
        assert alerts[0].level == "critical"
        assert "GAS Leak Detected" in alerts[0].title

    def test_water_leak_detection(self):
        reading = SensorReading(
            sensor_id="test_water",
            type="water",
            value=1.0,  #Water detected true/1
            location="Kitchen"
        )

        alerts = process_reading(reading)
        assert len(alerts) == 1
        assert alerts[0].level == "warning"
        assert "Water Leak" in alerts[0].title

    def test_fire_detection(self):
        reading = SensorReading(
            sensor_id="test_smoke",
            type="smoke",
            value=0.8, #Threshold is 0.6
            location="Kitchen"
        )

        alerts = process_reading(reading)
        assert len(alerts) == 1
        assert alerts[0].level == "critical"
        assert "FIRE DETECTED" in alerts[0].title
