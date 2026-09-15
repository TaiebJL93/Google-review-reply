import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")

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


def signup(client, email="owner@example.com", password="password123"):
    """Signs up and logs in a fresh user; TestClient persists the resulting
    session cookie across subsequent requests on the same client instance."""
    response = client.post(
        "/signup", data={"email": email, "password": password}, follow_redirects=False
    )
    assert response.status_code == 303, response.text
    return email
