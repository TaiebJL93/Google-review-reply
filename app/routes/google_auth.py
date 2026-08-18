from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.google_client import (
    build_authorize_url,
    exchange_code_for_tokens,
    list_accounts,
    list_locations,
)
from app.models import Business, GoogleConnection, Review
from app.sources.google_source import GoogleBusinessSource

router = APIRouter()


@router.get("/businesses/{business_id}/google/connect")
def connect(business_id: int, db: Session = Depends(get_db)):
    """Kicks off the OAuth consent flow. business_id rides in `state` since the
    registered redirect URI is fixed and can't carry a dynamic path segment."""
    _get_business_or_404(db, business_id)
    return RedirectResponse(url=build_authorize_url(state=str(business_id)))


@router.get("/auth/google/callback")
def callback(code: str, state: str, db: Session = Depends(get_db)):
    business = _get_business_or_404(db, int(state))

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
def disconnect(business_id: int, db: Session = Depends(get_db)):
    business = _get_business_or_404(db, business_id)
    if business.google_connection is not None:
        db.delete(business.google_connection)
        db.commit()
    return RedirectResponse(url=f"/businesses/{business_id}/dashboard", status_code=303)


@router.post("/businesses/{business_id}/google/sync")
def sync(business_id: int, db: Session = Depends(get_db)):
    business = _get_business_or_404(db, business_id)
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


def _get_business_or_404(db: Session, business_id: int) -> Business:
    business = db.get(Business, business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found.")
    return business
