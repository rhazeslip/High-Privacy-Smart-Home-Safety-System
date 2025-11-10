import pytest
import asyncio
from fastapi.testclient import TestClient
from backend.main import app
from backend.store import ALERTS, SENSOR_LAST


@pytest.fixture(autouse=True)
def clear_store_every_test():
    # Ensure each test runs with a clean in-memory and persisted store.
    try:
        from backend import store as _store
        ALERTS.clear()
        SENSOR_LAST.clear()
        cur = _store._DB.cursor()
        cur.execute("DELETE FROM alerts")
        cur.execute("DELETE FROM sensors")
        cur.execute("DELETE FROM refresh_tokens")
        cur.execute("DELETE FROM settings")
        _store._DB.commit()
    except Exception:
        pass
    yield
    # cleanup after test as well
    try:
        from backend import store as _store
        ALERTS.clear()
        SENSOR_LAST.clear()
        cur = _store._DB.cursor()
        cur.execute("DELETE FROM alerts")
        cur.execute("DELETE FROM sensors")
        cur.execute("DELETE FROM refresh_tokens")
        cur.execute("DELETE FROM settings")
        _store._DB.commit()
    except Exception:
        pass

@pytest.fixture(scope="function")
def test_client():
    ALERTS.clear()
    SENSOR_LAST.clear()

    with TestClient(app) as client:
        yield client
    
@pytest.fixture
def sample_sensor_data():
    return {
        "sensor_id": "test_door_1",
        "type": "door",
        "value": "open",
        "location": "Test Location"
    }

@pytest.fixture
def admin_credentials():
    return {"username": "admin", "password": "admin123"}

@pytest.fixture
def auth_headers(test_client, admin_credentials):
    response = test_client.post("/auth/login", json=admin_credentials)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}