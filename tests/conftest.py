"""Shared pytest fixtures: isolated DB + authenticated TestClient."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Point config at a temp SQLite DB and a known secret BEFORE app import.
_TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP_DB.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.name.replace(os.sep, '/')}"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only-0123456789"
os.environ["GEMINI_API_KEY"] = ""  # force fallback mode

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def _auth_user(client):
    """Register-or-login factory; returns the user JSON. Sets the auth cookie."""
    def _make(email: str, full_name: str, password: str = "password123") -> dict:
        r = client.post("/register", json={"email": email, "full_name": full_name, "password": password})
        if r.status_code == 409:  # already registered in a previous test
            r = client.post("/login", json={"email": email, "password": password})
        assert r.status_code in (200, 201), r.text
        return r.json()["user"]
    return _make


@pytest.fixture()
def user_a(client, _auth_user):
    """Logged-in user A (auth cookie set on the client)."""
    return _auth_user("alice@example.com", "Alice Alpha")


@pytest.fixture()
def user_b(client, _auth_user):
    """Logged-in user B (replaces A's cookie on the client)."""
    return _auth_user("bob@example.com", "Bob Beta")


VALID_HOME = {
    "total_budget": 50000,
    "rooms": [{"room_type": "Living Room", "quantity": 1}],
    "furniture": True,
    "lighting": True,
    "decor": True,
}

VALID_PARTY = {
    "total_budget": 30000,
    "guest_count": 20,
    "event_type": "birthday",
    "entertainment": True,
}

# Minimal valid 1x1 transparent PNG (9?? bytes)
PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c6360000002000154a24f5f0000000049454e44ae426082"
)
