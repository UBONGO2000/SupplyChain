"""Authentication and privilege-escalation regression tests.

These tests lock the Phase 0 security fixes: public registration must never
grant a privilege, and a deactivated account must lose access immediately.
"""

import pytest

import database
import main
from auth import verify_password
from models import User, UserRole

STRONG_PASSWORD = "Str0ngPass!"


# ============================================
# SEC-01 - no privilege through public registration
# ============================================
@pytest.mark.parametrize("role", ["admin", "manager", "staff", "viewer"])
def test_register_rejects_any_role_field(client, db, role):
    """A client must not be able to choose its own role (mass assignment)."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "attacker@example.com",
            "username": "attacker",
            "password": STRONG_PASSWORD,
            "role": role,
        },
    )

    assert response.status_code == 422
    assert db.query(User).count() == 0


def test_register_rejects_extra_privilege_flags(client, db):
    """`is_active`/`is_verified` are equally forbidden on sign-up."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "attacker@example.com",
            "username": "attacker",
            "password": STRONG_PASSWORD,
            "is_active": True,
            "is_verified": True,
        },
    )

    assert response.status_code == 422
    assert db.query(User).count() == 0


def test_register_assigns_least_privilege_role(client, db):
    """Without a role field, the account is created as a read-only viewer."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "newcomer@example.com",
            "username": "newcomer",
            "password": STRONG_PASSWORD,
            "full_name": "New Comer",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "viewer"
    assert "hashed_password" not in body
    assert "password" not in body

    user = db.query(User).filter(User.username == "newcomer").one()
    assert user.role == UserRole.VIEWER
    assert user.hashed_password != STRONG_PASSWORD
    assert user.hashed_password.startswith("$2")


def test_registered_viewer_cannot_write(client):
    """The least-privilege role must actually be enforced by the RBAC layer."""
    client.post(
        "/api/auth/register",
        json={
            "email": "viewer@example.com",
            "username": "viewer",
            "password": STRONG_PASSWORD,
        },
    )
    token = client.post(
        "/api/auth/login",
        json={"username": "viewer", "password": STRONG_PASSWORD},
    ).json()["access_token"]

    response = client.post(
        "/api/warehouses",
        json={"name": "Should not exist"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_register_rejects_duplicate_email(client, make_user):
    make_user(username="existing", email="taken@example.com")

    response = client.post(
        "/api/auth/register",
        json={
            "email": "taken@example.com",
            "username": "another",
            "password": STRONG_PASSWORD,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


def test_register_rejects_weak_password(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "weak@example.com",
            "username": "weak",
            "password": "alllowercase1",
        },
    )

    assert response.status_code == 422


# ============================================
# Login / current user
# ============================================
def test_login_returns_token_and_profile(client, make_user):
    make_user(username="alice")

    response = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": STRONG_PASSWORD},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == "alice"

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


def test_login_accepts_email_as_identifier(client, make_user):
    make_user(username="alice")

    response = client.post(
        "/api/auth/login",
        json={"username": "alice@example.com", "password": STRONG_PASSWORD},
    )

    assert response.status_code == 200


def test_login_with_wrong_password_is_rejected(client, make_user):
    make_user(username="alice")

    response = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "WrongPassword1!"},
    )

    assert response.status_code == 401


def test_me_requires_a_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_a_forged_token(client):
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not.a.real.token"},
    )

    assert response.status_code == 401


# ============================================
# SEC-04 - a deactivated account loses access immediately
# ============================================
def test_deactivated_user_token_is_rejected(client, db, make_user, token_for):
    user = make_user(username="alice")
    headers = {"Authorization": f"Bearer {token_for('alice')}"}

    assert client.get("/api/auth/me", headers=headers).status_code == 200

    user.is_active = False
    db.commit()

    assert client.get("/api/auth/me", headers=headers).status_code == 401


# ============================================
# SEC-02 - no hardcoded accounts anymore
# ============================================
def test_startup_creates_no_default_account(client, db):
    """The four published demo accounts must never be recreated."""
    assert db.query(User).count() == 0


def test_bootstrap_is_opt_in(client, db, monkeypatch, session_factory):
    monkeypatch.setattr(database, "SessionLocal", session_factory)

    main.bootstrap_admin()

    assert db.query(User).count() == 0


def test_bootstrap_creates_admin_from_environment(
    client, db, monkeypatch, session_factory
):
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    monkeypatch.setattr(main, "BOOTSTRAP_ADMIN_EMAIL", "boss@example.com")
    monkeypatch.setattr(main, "BOOTSTRAP_ADMIN_PASSWORD", "BootstrapPass123!")
    monkeypatch.setattr(main, "BOOTSTRAP_ADMIN_USERNAME", None)

    main.bootstrap_admin()

    user = db.query(User).filter(User.email == "boss@example.com").one()
    assert user.username == "boss"
    assert user.role == UserRole.ADMIN
    assert verify_password("BootstrapPass123!", user.hashed_password)

    # Idempotent: a redeploy must not duplicate or reset the account.
    main.bootstrap_admin()
    assert db.query(User).filter(User.email == "boss@example.com").count() == 1


def test_bootstrap_requires_both_credentials(client, monkeypatch, session_factory):
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    monkeypatch.setattr(main, "BOOTSTRAP_ADMIN_EMAIL", "boss@example.com")
    monkeypatch.setattr(main, "BOOTSTRAP_ADMIN_PASSWORD", None)

    with pytest.raises(ValueError):
        main.bootstrap_admin()


def test_bootstrap_rejects_a_short_password(client, db, monkeypatch, session_factory):
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    monkeypatch.setattr(main, "BOOTSTRAP_ADMIN_EMAIL", "boss@example.com")
    monkeypatch.setattr(main, "BOOTSTRAP_ADMIN_PASSWORD", "short")

    with pytest.raises(ValueError):
        main.bootstrap_admin()

    assert db.query(User).count() == 0
