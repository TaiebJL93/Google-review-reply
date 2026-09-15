"""Password hashing, session helpers, and the dependencies routes use to
require a signed-in user and to scope businesses to their owner."""

import hashlib
import hmac
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Business, User

# OWASP's 2023 recommendation for PBKDF2-HMAC-SHA256. Stored alongside each
# hash so it can be raised later without invalidating existing passwords.
PBKDF2_ITERATIONS = 600_000
_ALGORITHM = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS
    ).hex()
    return f"{_ALGORITHM}${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algorithm != _ALGORITHM:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), int(iterations)
    ).hex()
    return hmac.compare_digest(candidate, digest)


class LoginRequired(Exception):
    """Raised by page routes when nobody is signed in; app.main turns it into
    a redirect to /login so the user lands back where they were afterwards."""


def login_user(request: Request, user: User) -> None:
    request.session["user_id"] = user.id
    # Kept in the cookie purely so base.html can show it without a DB hit.
    request.session["user_email"] = user.email


def logout_user(request: Request) -> None:
    request.session.clear()


def _session_user(request: Request, db: Session) -> Optional[User]:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None:
        # Stale cookie from a database that has since been reset.
        request.session.clear()
    return user


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """For routes that render a page: signed-out visitors get sent to /login."""
    user = _session_user(request, db)
    if user is None:
        raise LoginRequired()
    return user


def current_user_api(request: Request, db: Session = Depends(get_db)) -> User:
    """For routes called from fetch() in app.js: a redirect would be followed
    silently and the login page's HTML injected into the review card, so
    return a 401 the front-end can display instead."""
    user = _session_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return user


def get_owned_business(db: Session, user: User, business_id: int) -> Business:
    """404 rather than 403 for someone else's business, so IDs can't be probed."""
    business = db.get(Business, business_id)
    if business is None or business.user_id != user.id:
        raise HTTPException(status_code=404, detail="Business not found.")
    return business
