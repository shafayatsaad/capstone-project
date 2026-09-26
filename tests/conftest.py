"""
Sets env vars *before* the app is imported anywhere (Settings reads os.getenv
at import time), points the app at a throwaway SQLite file, and makes the rate
limit small and deterministic so test_rate_limiting.py can trip it on purpose
without needing 20+ requests.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["GEO_MODE"] = "mock"
os.environ["RATE_LIMIT_SUBMISSIONS"] = "3/minute"
os.environ["FORCE_NOTIFY_FAIL"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine, SessionLocal
from app.main import app
from app.models import Owner, Widget
from app.rate_limit import limiter

TEST_WIDGET_ID = "11111111-1111-1111-1111-111111111111"
TEST_OWNER_ID = "11111111-1111-1111-1111-111111111112"


@pytest.fixture(scope="session", autouse=True)
def _create_schema_and_seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add(Owner(id=TEST_OWNER_ID, email="test@example.com", password_hash="x"))
    db.add(
        Widget(
            id=TEST_WIDGET_ID,
            owner_id=TEST_OWNER_ID,
            type="signup_form",
            title="Test widget",
            fields=[{"name": "email", "label": "Email", "type": "email", "required": True}],
        )
    )
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Every test starts with a clean rate-limit counter, so tests are
    order-independent except test_rate_limiting.py, which deliberately fills
    the bucket itself."""
    limiter.reset()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()
