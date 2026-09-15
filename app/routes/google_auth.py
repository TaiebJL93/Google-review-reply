import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import current_user, get_owned_business
from app.config import settings
from app.database import get_db
from app.google_client import (
    build_authorize_url,
    exchange_code_for_tokens,
    list_accounts,
    list_locations,
)
from app.models import GoogleConnection, Review, User
from app.sources.google_source import GoogleBusinessSource

router = APIRouter()

OAUTH_STATE_SESSION_KEY = "google_oauth_state"


@router.get("/businesses/{business_id}/google/connect")
def connect(
    request: Request,
    business_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Kicks off the OAuth consent flow. business_id rides in `state` since the
    registered redirect URI is fixed and can't carry a dynamic path segment.
    A random nonce is appended and remembered in the session so the callback
    can reject a `state` that this browser never initiated (login CSRF)."""
    get_owned_business(db, user, business_id)

    if not settings.google_client_id or not settings.google_client_secret:
        # Without this check, build_authorize_url() still returns a URL —
        # just one with an empty client_id — and Google's own error page
        # ("Missing required parameter: client_id") is the first anyone
        # hears about it. Catch it here instead so the failure is explained
        # in-app, on the same domain, with a way back.
        return RedirectResponse(
            url=f"/businesses/{business_id}/dashboard?google_error=not_configured",
            status_code=303,
        )

    state = f"{business_id}:{secrets.token_urlsafe(16)}"
    request.session[OAUTH_STATE_SESSION_KEY] = state
    return RedirectResponse(url=build_authorize_url(state=state))


@router.get("/auth/google/callback")
def callback(
    request: Request,
    code: str,
    state: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    expected_state = request.session.pop(OAUTH_STATE_SESSION_KEY, None)
    if expected_state is None or not secrets.compare_digest(state, expected_state):
        raise HTTPException(
            status_code=400,
            detail="This Google sign-in didn't start from ReviewReply. Click Connect Google again.",
        )
    business = get_owned_business(db, user, int(state.split(":", 1)[0]))

    tokens = exchange_code_for_tokens(code)
    if not tokens.refresh_token:
        raise HTTPException(
            status_code=400,
            detail="Google did not return a refresh token. Revoke this app's access at "
            "myaccount.google.com/permissions and try connecting again.",
        )

    accounts = list_accounts(tokens.access_token)
    if not accounts:
        raise HTTPException(
            status_code=400,
            detail="No Google Business Profile accounts found for this Google login.",
        )
    account_name = accounts[0]["name"]

    locations = list_locations(tokens.access_token, account_name)
    if not locations:
        raise HTTPException(
            status_code=400,
            detail="No Business Profile locations found on this account.",
        )
    # MVP simplification: auto-connect the first location. A business with
    # multiple locations would need a picker step here instead.
    location_name = locations[0]["name"]

    connection = business.google_connection
    if connection is None:
        connection = GoogleConnection(business_id=business.id)
        db.add(connection)

    connection.access_token = tokens.access_token
    connection.refresh_token = tokens.refresh_token
    connection.token_expires_at = datetime.utcnow() + timedelta(seconds=tokens.expires_in)
    connection.account_name = account_name
    connection.location_name = location_name
    db.commit()

    return RedirectResponse(url=f"/businesses/{business.id}/dashboard", status_code=303)


@router.post("/businesses/{business_id}/google/disconnect")
def disconnect(
    business_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    business = get_owned_business(db, user, business_id)
    if business.google_connection is not None:
        db.delete(business.google_connection)
        db.commit()
    return RedirectResponse(url=f"/businesses/{business_id}/dashboard", status_code=303)


@router.post("/businesses/{business_id}/google/sync")
def sync(
    business_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    business = get_owned_business(db, user, business_id)
    connection = business.google_connection
    if connection is None:
        raise HTTPException(
            status_code=400, detail="Connect a Google Business Profile account before syncing."
        )

    reviews_data = GoogleBusinessSource(connection).fetch()

    newest_seen = connection.last_synced_review_time
    for data in reviews_data:
        if data.external_id:
            already_synced = (
                db.query(Review).filter(Review.google_review_id == data.external_id).first()
            )
            if already_synced:
                continue

        db.add(
            Review(
                business_id=business.id,
                source="google",
                author_name=data.author_name,
                rating=data.rating,
                body=data.body,
                review_date=data.review_date,
                google_review_id=data.external_id,
            )
        )

        if data.review_date:
            seen_at = datetime.combine(data.review_date, datetime.min.time())
            if newest_seen is None or seen_at > newest_seen:
                newest_seen = seen_at

    connection.last_synced_review_time = newest_seen
    db.commit()

    return RedirectResponse(url=f"/businesses/{business_id}/dashboard", status_code=303)
