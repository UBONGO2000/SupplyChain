"""
Priority 1 -- Auth & security.

Covers registration, login, JWT validation, and role-based access control
(require_role). This is the foundation everything else depends on.
"""
from datetime import timedelta

import pytest

import models
from auth import create_access_token, verify_password
from conftest import make_user, auth_headers

VALID_PASSWORD = "Passw0rd123"


def _register_payload(**overrides):
    payload = {
        "email": "newuser@example.com",
        "username": "newuser",
        "full_name": "New User",
        "role": "staff",
        "password": VALID_PASSWORD,
    }
    payload.update(overrides)
    return payload


# ============================================
# Register
# ============================================
class TestRegister:
    def test_register_success_assigns_role_and_hashes_password(self, client, db_session):
        resp = client.post("/api/auth/register", json=_register_payload(role="manager"))

        assert resp.status_code == 201
        body = resp.json()
        assert body["role"] == "manager"
        assert "password" not in body
        assert "hashed_password" not in body

        db_user = db_session.query(models.User).filter(models.User.username == "newuser").first()
        assert db_user is not None
        assert db_user.role.value == "manager"
        # The core security property: the stored hash is never the raw password.
        assert db_user.hashed_password != VALID_PASSWORD
        assert verify_password(VALID_PASSWORD, db_user.hashed_password) is True

    def test_register_duplicate_email_rejected(self, client):
        first = client.post("/api/auth/register", json=_register_payload(username="first"))
        assert first.status_code == 201

        resp = client.post(
            "/api/auth/register",
            json=_register_payload(username="second", email="newuser@example.com"),
        )

        assert resp.status_code == 400
        assert "email" in resp.json()["detail"].lower()

    def test_register_duplicate_username_rejected(self, client):
        first = client.post("/api/auth/register", json=_register_payload(email="first@example.com"))
        assert first.status_code == 201

        resp = client.post(
            "/api/auth/register",
            json=_register_payload(email="second@example.com"),
        )

        assert resp.status_code == 400
        assert "username" in resp.json()["detail"].lower()


# ============================================
# Login
# ============================================
class TestLogin:
    def test_login_wrong_password_rejected(self, client, db_session):
        make_user(db_session, "bob", password=VALID_PASSWORD)

        resp = client.post("/api/auth/login", json={"username": "bob", "password": "WrongPass1"})

        assert resp.status_code == 401

    def test_login_nonexistent_user_rejected(self, client):
        resp = client.post(
            "/api/auth/login", json={"username": "ghost", "password": "WhoKnows1"}
        )

        assert resp.status_code == 401

    def test_login_inactive_user_rejected(self, client, db_session):
        make_user(db_session, "disabled", password=VALID_PASSWORD, is_active=False)

        resp = client.post(
            "/api/auth/login", json={"username": "disabled", "password": VALID_PASSWORD}
        )

        assert resp.status_code == 403

    def test_login_success_returns_token_and_user(self, client, db_session):
        make_user(db_session, "carol", password=VALID_PASSWORD, role="staff")

        resp = client.post(
            "/api/auth/login", json={"username": "carol", "password": VALID_PASSWORD}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
        assert body["user"]["username"] == "carol"


# ============================================
# JWT validation
# ============================================
class TestJWT:
    def test_expired_token_rejected(self, client, db_session):
        user = make_user(db_session, "dave")
        token = create_access_token(
            data={"sub": user.username, "user_id": user.id, "role": user.role.value},
            expires_delta=timedelta(minutes=-5),
        )

        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 401

    def test_malformed_token_rejected(self, client):
        resp = client.get(
            "/api/auth/me", headers={"Authorization": "Bearer not-a-real-jwt-token"}
        )

        assert resp.status_code == 401

    def test_tampered_token_rejected(self, client, db_session):
        user = make_user(db_session, "erin")
        token = create_access_token(
            data={"sub": user.username, "user_id": user.id, "role": user.role.value}
        )
        tampered = token[:-4] + ("A" if token[-4] != "A" else "B") + token[-3:]

        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered}"})

        assert resp.status_code == 401

    def test_me_returns_correct_user_for_token(self, client, db_session):
        user_a = make_user(db_session, "frank")
        user_b = make_user(db_session, "grace")

        resp = client.get("/api/auth/me", headers=auth_headers(user_a))

        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "frank"
        assert body["username"] != user_b.username


# ============================================
# RBAC (require_role)
# ============================================
class TestRBAC:
    def test_disallowed_role_gets_403(self, client, viewer_user):
        # Creating inventory requires admin/manager/staff -- viewer is excluded.
        resp = client.post(
            "/api/inventory",
            json={"warehouse_id": 1, "product_id": 1, "quantity": 10},
            headers=auth_headers(viewer_user),
        )

        assert resp.status_code == 403

    def test_allowed_role_passes_rbac_check(self, client, staff_user, warehouse, product):
        # staff is an allowed role for inventory creation; the request should
        # get past require_role (any later 4xx would be from business logic,
        # not RBAC).
        resp = client.post(
            "/api/inventory",
            json={"warehouse_id": warehouse.id, "product_id": product.id, "quantity": 10},
            headers=auth_headers(staff_user),
        )

        assert resp.status_code == 201


# ============================================
# Priority 4 -- unauthenticated access
# ============================================
@pytest.mark.parametrize(
    "method,url",
    [
        ("get", "/api/auth/me"),
        ("get", "/api/orders"),
        ("post", "/api/orders"),
        ("get", "/api/inventory"),
        ("post", "/api/inventory"),
        ("post", "/api/inventory/adjust?warehouse_id=1&product_id=1"),
        ("get", "/api/orders/1"),
    ],
)
def test_protected_routes_reject_unauthenticated_requests(client, method, url):
    if method == "post":
        resp = client.post(url, json={})
    else:
        resp = client.get(url)

    assert resp.status_code == 401
