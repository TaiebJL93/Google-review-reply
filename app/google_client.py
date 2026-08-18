from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlencode

import httpx

from app.config import settings

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ACCOUNTS_URL = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
LOCATIONS_URL_TMPL = "https://mybusinessbusinessinformation.googleapis.com/v1/{account_name}/locations"
REVIEWS_URL_TMPL = "https://mybusiness.googleapis.com/v4/{location_name}/reviews"

SCOPE = "https://www.googleapis.com/auth/business.manage"
REQUEST_TIMEOUT = 10


@dataclass
class TokenResponse:
    access_token: str
    refresh_token: Optional[str]
    expires_in: int


def build_authorize_url(state: str) -> str:
    """Builds the URL that starts the OAuth consent flow for a business owner.

    access_type=offline + prompt=consent are required to get a refresh_token
    back on the first authorization — Google only issues one when consent is
    freshly granted, not on repeat authorizations.
    """
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> TokenResponse:
    response = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    return TokenResponse(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_in=data.get("expires_in", 3600),
    )


def refresh_access_token(refresh_token: str) -> TokenResponse:
    response = httpx.post(
        TOKEN_URL,
        data={
            "refresh_token": refresh_token,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "grant_type": "refresh_token",
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    # Google does not re-issue a refresh_token on this call; keep the one we have.
    return TokenResponse(
        access_token=data["access_token"],
        refresh_token=refresh_token,
        expires_in=data.get("expires_in", 3600),
    )


def list_accounts(access_token: str) -> List[dict]:
    response = httpx.get(
        ACCOUNTS_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("accounts", [])


def list_locations(access_token: str, account_name: str) -> List[dict]:
    url = LOCATIONS_URL_TMPL.format(account_name=account_name)
    response = httpx.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        params={"readMask": "name,title"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("locations", [])


def list_reviews(access_token: str, location_name: str, page_token: Optional[str] = None) -> dict:
    url = REVIEWS_URL_TMPL.format(location_name=location_name)
    params = {"pageToken": page_token} if page_token else {}
    response = httpx.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()
