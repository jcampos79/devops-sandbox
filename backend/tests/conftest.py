"""Shared test fixtures.

Tests run against a real PostgreSQL database (not SQLite) because credit
concurrency tests rely on genuine row-level locking (`SELECT ... FOR
UPDATE`), which SQLite does not implement meaningfully. Point
TEST_DATABASE_URL at a disposable database; CI/dev setup is documented in
backend/README.md.
"""

import os

# Set BEFORE importing any app module -- app.config.get_settings() is
# lru_cached, so env vars must be present at first import for tests that
# exercise distribution-image lookups.
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "sandbox")
os.environ.setdefault("POSTGRES_PASSWORD", "sandbox")
os.environ.setdefault("POSTGRES_DB", "sandbox")
os.environ.setdefault("SANDBOX_IMAGE_UBUNTU", "test-registry/sandbox-ubuntu:24.04")
os.environ.setdefault("SANDBOX_IMAGE_ROCKY", "test-registry/sandbox-rocky:9")
os.environ.setdefault("SANDBOX_IMAGE_DEBIAN", "test-registry/sandbox-debian:13")
os.environ.setdefault("SANDBOX_IMAGE_ALPINE", "test-registry/sandbox-alpine:latest")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://sandbox:sandbox@localhost:5432/sandbox"
)

engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    Base.metadata.create_all(engine)
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))


@pytest.fixture
def db() -> Session:
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def db_session_factory():
    """For concurrency tests that need two independent sessions/connections."""
    return TestSessionLocal


@pytest.fixture
def client(db):  # noqa: ARG001 -- db fixture ensures tables exist/are cleaned
    """FastAPI TestClient wired to the same test database as the `db` fixture."""
    from app.database import get_db
    from app.main import app

    def override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(db, *, username="alice", password="s3cret!", is_admin=False, balance=0):
    """Shared helper: creates a user (optionally with an initial credit
    grant) and returns it."""
    from app.auth.security import hash_password
    from app.models import User
    from app.services.credits import admin_adjust_credits

    user = User(username=username, password_hash=hash_password(password), is_admin=is_admin)
    db.add(user)
    db.commit()
    db.refresh(user)
    if balance:
        admin_adjust_credits(db, user.id, balance, "test grant")
    return user


def login(client, username="alice", password="s3cret!") -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
