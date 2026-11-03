"""Phase 1 — reliable demo: landing page, demo account and seed safety."""

from auth import verify_password
from cli import create_demo_user, generate_password
from models import User, UserRole


# ============================================
# Landing page
# ============================================
def test_root_endpoint_is_self_describing(client):
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "1.0.0"
    assert body["docs"] == "/docs"
    assert body["health"] == "/health"
    assert "demo_credentials_hint" in body


# ============================================
# Demo account (CLI)
# ============================================
def test_generated_password_satisfies_the_api_policy():
    password = generate_password()

    assert len(password) >= 12
    assert any(char.isupper() for char in password)
    assert any(char.islower() for char in password)
    assert any(char.isdigit() for char in password)


def test_create_demo_user_is_usable_and_least_privileged(db):
    user, password = create_demo_user(db)

    assert user.email == "demo@example.com"
    assert user.username == "demo"
    assert user.role == UserRole.STAFF
    assert user.is_active is True
    assert password is not None
    assert verify_password(password, user.hashed_password)


def test_create_demo_user_rotates_the_password(db):
    user, first_password = create_demo_user(db)
    same_user, second_password = create_demo_user(db)

    assert same_user.id == user.id
    assert db.query(User).count() == 1
    assert first_password != second_password
    assert verify_password(second_password, same_user.hashed_password)
    assert not verify_password(first_password, same_user.hashed_password)


# ============================================
# Seed must never be fatal
# ============================================
def test_seed_reports_failure_instead_of_raising(monkeypatch):
    import seed_data

    def broken_session_factory():
        raise RuntimeError("database is down")

    monkeypatch.setattr(seed_data, "SessionLocal", broken_session_factory)

    assert seed_data.seed_demo_data() is False
