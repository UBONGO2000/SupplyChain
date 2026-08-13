"""
Priority 4 -- /health endpoint.
"""
import database


def test_health_accessible_without_authentication(client):
    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_health_reflects_connected_database(client, monkeypatch):
    monkeypatch.setattr(database, "check_database_connection", lambda: True)

    resp = client.get("/health")

    assert resp.json()["database"] == "connected"


def test_health_reflects_disconnected_database(client, monkeypatch):
    monkeypatch.setattr(database, "check_database_connection", lambda: False)

    resp = client.get("/health")

    assert resp.json()["database"] == "disconnected"
