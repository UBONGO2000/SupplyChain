"""Security primitives and infrastructure tests (Phase 0)."""

import pytest

import database
from auth import get_password_hash, verify_password


# ============================================
# DEP-01 - bcrypt works without passlib
# ============================================
def test_hash_is_bcrypt_and_verifiable():
    hashed = get_password_hash("Str0ngPass!")

    assert hashed.startswith("$2")
    assert "Str0ngPass!" not in hashed
    assert verify_password("Str0ngPass!", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_verify_never_raises_on_corrupted_hash():
    """A broken database row must produce a 401, not a 500."""
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_password_longer_than_72_bytes_is_rejected():
    """bcrypt ignores bytes beyond 72; refuse instead of truncating silently."""
    with pytest.raises(ValueError):
        get_password_hash("a" * 73)


def test_password_exactly_72_bytes_is_accepted():
    hashed = get_password_hash("a" * 72)
    assert verify_password("a" * 72, hashed) is True


# ============================================
# API-02 - /health is meaningful
# ============================================
def test_health_reports_connected_database(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["database"] == "connected"
    assert "timestamp" in body


def test_health_returns_503_when_database_is_down(client, monkeypatch):
    monkeypatch.setattr(database, "check_database_connection", lambda: False)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "disconnected"


# ============================================
# SEC-06 - no wildcard Vercel origin
# ============================================
def test_cors_allows_configured_origin(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert (
        response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    )


def test_cors_rejects_an_unlisted_vercel_deployment(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "https://attacker.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") is None
