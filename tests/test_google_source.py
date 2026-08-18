from datetime import datetime, timedelta

from app.google_client import TokenResponse
from app.models import GoogleConnection
from app.sources.google_source import GoogleBusinessSource


def _connection(**overrides):
    defaults = dict(
        business_id=1,
        access_token="old-token",
        refresh_token="refresh-token",
        token_expires_at=datetime.utcnow() + timedelta(hours=1),
        account_name="accounts/123",
        location_name="accounts/123/locations/456",
        last_synced_review_time=None,
    )
    defaults.update(overrides)
    return GoogleConnection(**defaults)


def test_fetch_maps_and_paginates_reviews(monkeypatch):
    connection = _connection()

    pages = [
        {
            "reviews": [
                {
                    "reviewId": "r1",
                    "reviewer": {"displayName": "Jane Doe"},
                    "starRating": "FIVE",
                    "comment": "Loved it!",
                    "updateTime": "2026-08-01T10:00:00Z",
                }
            ],
            "nextPageToken": "page2",
        },
        {
            "reviews": [
                {
                    "reviewId": "r2",
                    "reviewer": {"displayName": "Sam Lee"},
                    "starRating": "TWO",
                    "comment": "Slow service.",
                    "updateTime": "2026-08-02T10:00:00Z",
                }
            ]
        },
    ]
    calls = []

    def fake_list_reviews(access_token, location_name, page_token=None):
        calls.append(page_token)
        return pages[len(calls) - 1]

    monkeypatch.setattr("app.sources.google_source.list_reviews", fake_list_reviews)

    results = GoogleBusinessSource(connection).fetch()

    assert [r.author_name for r in results] == ["Jane Doe", "Sam Lee"]
    assert [r.rating for r in results] == [5, 2]
    assert [r.external_id for r in results] == ["r1", "r2"]
    assert calls == [None, "page2"]


def test_fetch_skips_reviews_at_or_before_last_sync(monkeypatch):
    connection = _connection(last_synced_review_time=datetime(2026, 8, 1))

    monkeypatch.setattr(
        "app.sources.google_source.list_reviews",
        lambda access_token, location_name, page_token=None: {
            "reviews": [
                {
                    "reviewId": "old",
                    "reviewer": {"displayName": "Old Review"},
                    "starRating": "FOUR",
                    "comment": "old",
                    "updateTime": "2026-07-31T10:00:00Z",
                },
                {
                    "reviewId": "new",
                    "reviewer": {"displayName": "New Review"},
                    "starRating": "FOUR",
                    "comment": "new",
                    "updateTime": "2026-08-02T10:00:00Z",
                },
            ]
        },
    )

    results = GoogleBusinessSource(connection).fetch()
    assert [r.external_id for r in results] == ["new"]


def test_fetch_refreshes_expired_access_token(monkeypatch):
    connection = _connection(token_expires_at=datetime.utcnow() - timedelta(minutes=1))

    monkeypatch.setattr(
        "app.sources.google_source.refresh_access_token",
        lambda refresh_token: TokenResponse(
            access_token="new-token", refresh_token=refresh_token, expires_in=3600
        ),
    )

    seen_tokens = []

    def fake_list_reviews(access_token, location_name, page_token=None):
        seen_tokens.append(access_token)
        return {"reviews": []}

    monkeypatch.setattr("app.sources.google_source.list_reviews", fake_list_reviews)

    GoogleBusinessSource(connection).fetch()

    assert seen_tokens == ["new-token"]
    assert connection.access_token == "new-token"


def test_unknown_star_rating_maps_to_zero(monkeypatch):
    connection = _connection()

    monkeypatch.setattr(
        "app.sources.google_source.list_reviews",
        lambda access_token, location_name, page_token=None: {
            "reviews": [
                {
                    "reviewId": "r1",
                    "reviewer": {"displayName": "Jane Doe"},
                    "starRating": "STAR_RATING_UNSPECIFIED",
                    "comment": "no rating",
                    "updateTime": "2026-08-01T10:00:00Z",
                }
            ]
        },
    )

    results = GoogleBusinessSource(connection).fetch()
    assert results[0].rating == 0
