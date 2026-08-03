import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)
