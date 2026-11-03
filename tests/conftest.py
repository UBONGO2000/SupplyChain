"""Shared pytest fixtures.

The environment is configured *before* importing the application so that
`config.py` never picks up the real production settings from `.env`.
Tests run against a temporary SQLite file: no MySQL, no network, no side
effect on any real database.
"""

import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-with-at-least-32-characters"
os.environ["APP_ENV"] = "test"
os.environ["SEED_DEMO_DATA"] = "false"
# Empty strings (not pop) on purpose: load_dotenv() never overrides a variable
# that already exists, so a developer's .env can never leak into the tests.
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = ""
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = ""
os.environ["BOOTSTRAP_ADMIN_USERNAME"] = ""
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["CORS_ORIGIN_REGEX"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from auth import get_password_hash
from database import Base, get_db
from models import User, UserRole

DEFAULT_PASSWORD = "Str0ngPass!"


@pytest.fixture()
def session_factory(tmp_path):
    """A fresh SQLite database and session factory for each test."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    yield factory

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db(session_factory):
    """A session for arranging and asserting data."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(session_factory):
    """HTTP client bound to the test database (no startup side effects)."""

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db):
    """Factory that inserts a user directly, bypassing the API."""

    def _make(
        username: str = "alice",
        email: str | None = None,
        password: str = DEFAULT_PASSWORD,
        role: UserRole = UserRole.VIEWER,
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email or f"{username}@example.com",
            username=username,
            hashed_password=get_password_hash(password),
            full_name=username.title(),
            role=role,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture()
def token_for(client):
    """Log a user in and return its bearer token."""

    def _token(username: str = "alice", password: str = DEFAULT_PASSWORD) -> str:
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    return _token


@pytest.fixture()
def auth_headers(token_for):
    """Ready-to-use Authorization header for the default user."""

    def _headers(username: str = "alice", password: str = DEFAULT_PASSWORD) -> dict:
        return {"Authorization": f"Bearer {token_for(username, password)}"}

    return _headers
