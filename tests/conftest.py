"""
Shared pytest fixtures for the Supply Chain API test suite.

Strategy:
- config.py requires DATABASE_URL to be set at import time, and database.py's
  engine is built with MySQL-only connect_args (charset/ssl). We satisfy the
  import-time requirement with a fake, never-dialed MySQL URL (SQLAlchemy
  engines are lazy: create_engine() doesn't actually connect), then point the
  app's `get_db` dependency at a real, separate SQLite-in-memory engine for
  actual test I/O.
- APP_ENV=test disables the bootstrap administrator and the demo seed at
  startup, so tests never touch a real database.
- The Phase 0/1 suite also uses `db`, `session_factory` and `token_for`
  aliases; they are kept below for compatibility.
"""

import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DATABASE_URL", "mysql+pymysql://user:pass@127.0.0.1:3306/testdb")
os.environ.setdefault(
    "SECRET_KEY", "test-only-secret-key-not-for-production-use-32chars"
)
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SEED_DEMO_DATA", "false")
os.environ.setdefault("BOOTSTRAP_ADMIN_EMAIL", "")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "")
os.environ.setdefault("BOOTSTRAP_ADMIN_USERNAME", "")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("CORS_ORIGIN_REGEX", "")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import database
import models
from main import app
from auth import get_password_hash, create_access_token

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine, expire_on_commit=False
)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[database.get_db] = _override_get_db


@pytest.fixture(autouse=True)
def fresh_db():
    """Fresh schema for every test -- avoids order-dependent test pollution."""
    models.Base.metadata.create_all(bind=test_engine)
    yield
    models.Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def healthy_database(monkeypatch):
    """Default /health to a reachable DB.

    The app engine points at a fake, never-dialed MySQL URL (see module
    docstring), so `check_database_connection()` would always report a
    failure. Tests that specifically exercise the unhealthy path override
    this patch with `monkeypatch.setattr(..., lambda: False)`.
    """
    monkeypatch.setattr(database, "check_database_connection", lambda: True)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def db(db_session):
    """Compatibility alias used by the Phase 0/1 test suite."""
    return db_session


@pytest.fixture
def session_factory():
    """Session factory for tests that monkeypatch database.SessionLocal."""
    return TestingSessionLocal


@pytest.fixture
def client():
    # Deliberately NOT used as a context manager: that would trigger the
    # app's lifespan. APP_ENV=test already disables bootstrap/seed, but
    # avoiding lifespan keeps the fixture fast and side-effect free.
    return TestClient(app)


@pytest.fixture
def token_for(client):
    """Log a user in through the API and return its bearer token."""

    def _token(username="alice", password="Str0ngPass!"):
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    return _token


# ============================================
# Domain fixtures
# ============================================
def make_user(
    db_session,
    username,
    role="staff",
    password="Passw0rd123",
    email=None,
    is_active=True,
):
    user = models.User(
        email=email or f"{username}@example.com",
        username=username,
        hashed_password=get_password_hash(password),
        full_name=username.title(),
        role=models.UserRole(role) if isinstance(role, str) else role,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(user):
    token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role.value}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_user(db_session):
    return make_user(db_session, "admin_test", role="admin", password="AdminPass1")


@pytest.fixture
def manager_user(db_session):
    return make_user(
        db_session, "manager_test", role="manager", password="ManagerPass1"
    )


@pytest.fixture
def staff_user(db_session):
    return make_user(db_session, "staff_test", role="staff", password="StaffPass1")


@pytest.fixture
def viewer_user(db_session):
    return make_user(db_session, "viewer_test", role="viewer", password="ViewerPass1")


@pytest.fixture
def warehouse(db_session):
    wh = models.Warehouse(
        name="Main Warehouse", location="Paris", capacity_m3=Decimal("1000.00")
    )
    db_session.add(wh)
    db_session.commit()
    db_session.refresh(wh)
    return wh


def make_product(db_session, sku="SKU-001", unit_price="10.00"):
    product = models.Product(
        sku=sku,
        name=f"Product {sku}",
        category=models.ProductCategory.ELECTRONICS,
        unit_price=Decimal(unit_price),
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture
def product(db_session):
    return make_product(db_session)


def make_inventory(db_session, warehouse, product, quantity=100, reserved_quantity=0):
    inv = models.Inventory(
        warehouse_id=warehouse.id,
        product_id=product.id,
        quantity=quantity,
        reserved_quantity=reserved_quantity,
        available_quantity=quantity - reserved_quantity,
        reorder_level=10,
    )
    db_session.add(inv)
    db_session.commit()
    db_session.refresh(inv)
    return inv
