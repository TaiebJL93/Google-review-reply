from tests.conftest import signup


def test_signup_creates_account_and_redirects_to_setup(client):
    response = client.post(
        "/signup",
        data={"email": "owner@example.com", "password": "password123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    # Session cookie from signup is enough to reach the authenticated area.
    follow_up = client.get("/", follow_redirects=False)
    assert follow_up.headers["location"] == "/setup"


def test_signup_duplicate_email_returns_error(client):
    signup(client, email="owner@example.com")
    client.post("/logout")

    response = client.post(
        "/signup",
        data={"email": "owner@example.com", "password": "different123"},
    )
    assert response.status_code == 422
    assert "already exists" in response.text.lower()


def test_signup_short_password_returns_error(client):
    response = client.post(
        "/signup", data={"email": "owner@example.com", "password": "short"}
    )
    assert response.status_code == 422
    assert "8 characters" in response.text


def test_signup_invalid_email_returns_error(client):
    response = client.post(
        "/signup", data={"email": "not-an-email", "password": "password123"}
    )
    assert response.status_code == 422
    assert "valid email" in response.text.lower()


def test_login_with_correct_credentials_succeeds(client):
    signup(client, email="owner@example.com", password="password123")
    client.post("/logout")

    response = client.post(
        "/login",
        data={"email": "owner@example.com", "password": "password123", "next": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_login_with_wrong_password_returns_error(client):
    signup(client, email="owner@example.com", password="password123")
    client.post("/logout")

    response = client.post(
        "/login",
        data={"email": "owner@example.com", "password": "wrong-password", "next": ""},
    )
    assert response.status_code == 422
    assert "invalid email or password" in response.text.lower()


def test_login_respects_next_param(client):
    signup(client, email="owner@example.com", password="password123")
    client.post("/logout")

    response = client.post(
        "/login",
        data={"email": "owner@example.com", "password": "password123", "next": "/setup"},
        follow_redirects=False,
    )
    assert response.headers["location"] == "/setup"


def test_login_ignores_unsafe_next_param(client):
    signup(client, email="owner@example.com", password="password123")
    client.post("/logout")

    response = client.post(
        "/login",
        data={
            "email": "owner@example.com",
            "password": "password123",
            "next": "https://evil.example.com",
        },
        follow_redirects=False,
    )
    assert response.headers["location"] == "/"


def test_logout_clears_session(client):
    signup(client)
    client.post("/logout")

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_signed_out_visitor_is_redirected_to_login_with_next(client):
    response = client.get("/businesses/1/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=%2Fbusinesses%2F1%2Fdashboard"


def test_cannot_access_another_users_business(client):
    signup(client, email="first@example.com")
    create_response = client.post(
        "/businesses",
        data={"name": "Java Hut", "business_type": "coffee shop", "owner_name": "Maria"},
        follow_redirects=False,
    )
    business_id = int(create_response.headers["location"].split("/")[2])
    client.post("/logout")

    signup(client, email="second@example.com")
    response = client.get(f"/businesses/{business_id}/dashboard")
    assert response.status_code == 404
