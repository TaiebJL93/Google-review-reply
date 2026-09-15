from urllib.parse import parse_qs, urlparse

from app.google_client import TokenResponse
from tests.conftest import signup


def _create_business(client):
    signup(client)
    response = client.post(
        "/businesses",
        data={"name": "Java Hut", "business_type": "coffee shop", "owner_name": "Maria Ortiz"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(response.headers["location"].split("/")[2])


def _mock_oauth_exchange(monkeypatch, refresh_token="refresh-token"):
    monkeypatch.setattr(
        "app.routes.google_auth.exchange_code_for_tokens",
        lambda code: TokenResponse(
            access_token="access-token", refresh_token=refresh_token, expires_in=3600
        ),
    )
    monkeypatch.setattr(
        "app.routes.google_auth.list_accounts",
        lambda access_token: [{"name": "accounts/123"}],
    )
    monkeypatch.setattr(
        "app.routes.google_auth.list_locations",
        lambda access_token, account_name: [{"name": "accounts/123/locations/456", "title": "Java Hut"}],
    )


def _connect_and_get_state(client, business_id):
    """Mirrors what a browser does: hit /connect to stash the CSRF nonce in
    the session, then read the `state` Google would echo back on /callback."""
    connect_response = client.get(f"/businesses/{business_id}/google/connect", follow_redirects=False)
    assert connect_response.status_code == 307
    query = parse_qs(urlparse(connect_response.headers["location"]).query)
    return query["state"][0]


def _run_callback(client, business_id, **kwargs):
    state = _connect_and_get_state(client, business_id)
    return client.get(
        "/auth/google/callback",
        params={"code": "auth-code", "state": state},
        **kwargs,
    )


def test_connect_redirects_to_google_authorize_url(client):
    business_id = _create_business(client)

    response = client.get(f"/businesses/{business_id}/google/connect", follow_redirects=False)

    assert response.status_code == 307
    assert "accounts.google.com" in response.headers["location"]
    assert f"state={business_id}%3A" in response.headers["location"]


def test_connect_for_unknown_business_returns_404(client):
    signup(client)
    response = client.get("/businesses/9999/google/connect", follow_redirects=False)
    assert response.status_code == 404


def test_connect_without_google_credentials_redirects_with_error(client, monkeypatch):
    """Without this guard, connect() still redirects to Google, just with an
    empty client_id — Google's own error page is the only signal anyone gets."""
    business_id = _create_business(client)
    monkeypatch.setattr("app.routes.google_auth.settings.google_client_id", "")

    response = client.get(f"/businesses/{business_id}/google/connect", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == f"/businesses/{business_id}/dashboard?google_error=not_configured"

    dashboard = client.get(response.headers["location"])
    assert "GOOGLE_CLIENT_ID" in dashboard.text


def test_callback_with_tampered_state_returns_400(client, monkeypatch):
    business_id = _create_business(client)
    _mock_oauth_exchange(monkeypatch)
    _connect_and_get_state(client, business_id)  # stashes the real nonce in the session

    response = client.get(
        "/auth/google/callback",
        params={"code": "auth-code", "state": f"{business_id}:not-the-real-nonce"},
    )
    assert response.status_code == 400


def test_callback_creates_connection_and_redirects_to_dashboard(client, monkeypatch):
    business_id = _create_business(client)
    _mock_oauth_exchange(monkeypatch)

    response = _run_callback(client, business_id, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == f"/businesses/{business_id}/dashboard"

    dashboard = client.get(f"/businesses/{business_id}/dashboard")
    assert "Google connected" in dashboard.text
    assert "Sync Google reviews" in dashboard.text


def test_callback_without_refresh_token_returns_400(client, monkeypatch):
    business_id = _create_business(client)
    _mock_oauth_exchange(monkeypatch, refresh_token=None)

    response = _run_callback(client, business_id)

    assert response.status_code == 400


def test_sync_without_connection_returns_400(client):
    business_id = _create_business(client)

    response = client.post(f"/businesses/{business_id}/google/sync")

    assert response.status_code == 400


def test_sync_persists_new_reviews_and_dedupes_on_second_sync(client, monkeypatch):
    business_id = _create_business(client)
    _mock_oauth_exchange(monkeypatch)
    _run_callback(client, business_id)

    monkeypatch.setattr(
        "app.sources.google_source.list_reviews",
        lambda access_token, location_name, page_token=None: {
            "reviews": [
                {
                    "reviewId": "r1",
                    "reviewer": {"displayName": "Jane Doe"},
                    "starRating": "FIVE",
                    "comment": "Loved the oat milk latte!",
                    "updateTime": "2026-08-01T10:00:00Z",
                }
            ]
        },
    )

    response = client.post(f"/businesses/{business_id}/google/sync", follow_redirects=False)
    assert response.status_code == 303

    dashboard = client.get(f"/businesses/{business_id}/dashboard")
    assert "Jane Doe" in dashboard.text
    assert dashboard.text.count("Loved the oat milk latte") == 1

    # Second sync sees the same review again — must not duplicate it.
    client.post(f"/businesses/{business_id}/google/sync")
    dashboard_after = client.get(f"/businesses/{business_id}/dashboard")
    assert dashboard_after.text.count("Loved the oat milk latte") == 1


def test_disconnect_removes_connection(client, monkeypatch):
    business_id = _create_business(client)
    _mock_oauth_exchange(monkeypatch)
    _run_callback(client, business_id)

    response = client.post(f"/businesses/{business_id}/google/disconnect", follow_redirects=False)
    assert response.status_code == 303

    dashboard = client.get(f"/businesses/{business_id}/dashboard")
    assert "Connect Google" in dashboard.text
    assert "Google connected" not in dashboard.text
