"""
Cross-cutting API behaviour.

Covers the pieces that are not tied to a domain: error mapping (a database
failure must never surface as a raw 500) and request tracing.
"""

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from conftest import auth_headers


# ============================================
# Request tracing
# ============================================
def test_request_id_is_generated_when_absent(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


def test_request_id_is_echoed_when_provided(client):
    response = client.get("/health", headers={"X-Request-ID": "trace-abc-123"})

    assert response.headers["X-Request-ID"] == "trace-abc-123"


# ============================================
# Database error mapping
# ============================================
def test_integrity_error_is_mapped_to_409(client, staff_user, monkeypatch):
    def boom(*args, **kwargs):
        raise IntegrityError("INSERT INTO orders", {}, Exception("duplicate"))

    monkeypatch.setattr("routers.orders.order_service.create_order", boom)

    response = client.post(
        "/api/orders",
        json={"items": [{"product_id": 1, "quantity": 1}]},
        headers=auth_headers(staff_user),
    )

    assert response.status_code == 409
    assert "conflict" in response.json()["detail"].lower()


def test_database_outage_is_mapped_to_503(client, staff_user, monkeypatch):
    def boom(*args, **kwargs):
        raise SQLAlchemyError("connection lost")

    monkeypatch.setattr("routers.orders.order_service.create_order", boom)

    response = client.post(
        "/api/orders",
        json={"items": [{"product_id": 1, "quantity": 1}]},
        headers=auth_headers(staff_user),
    )

    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"].lower()
