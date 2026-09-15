from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import hash_password, login_user, logout_user, verify_password
from app.database import get_db
from app.models import Business, User
from app.schemas import LoginForm, SignupForm
from app.templating import templates

router = APIRouter()


@router.get("/signup")
def signup_form(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request, "signup.html", {"errors": []})


@router.post("/signup")
def signup(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        data = SignupForm(email=email, password=password)
    except ValidationError as exc:
        return _signup_error(request, [e["msg"] for e in exc.errors()], email)

    if db.query(User).filter(User.email == data.email).first() is not None:
        return _signup_error(request, ["An account with this email already exists."], email)

    is_first_user = db.query(User).first() is None
    user = User(email=data.email, password_hash=hash_password(data.password))
    db.add(user)
    db.flush()

    if is_first_user:
        # Databases from before accounts existed hold businesses with no owner.
        # The first person to sign up on such a database is its owner, so
        # adopt them rather than leaving them unreachable.
        db.query(Business).filter(Business.user_id.is_(None)).update({"user_id": user.id})

    db.commit()
    login_user(request, user)
    return RedirectResponse(url="/", status_code=303)


@router.get("/login")
def login_form(request: Request, next: str = ""):
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"errors": [], "next": next})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        data = LoginForm(email=email, password=password)
    except ValidationError as exc:
        return _login_error(request, [e["msg"] for e in exc.errors()], email, next)

    user = db.query(User).filter(User.email == data.email).first()
    if user is None or not verify_password(data.password, user.password_hash):
        # Same message either way so the form doesn't reveal which emails exist.
        return _login_error(request, ["Invalid email or password."], email, next)

    login_user(request, user)
    return RedirectResponse(url=_safe_next(next), status_code=303)


@router.post("/logout")
def logout(request: Request):
    logout_user(request)
    return RedirectResponse(url="/login", status_code=303)


def _safe_next(next: str) -> str:
    """Only follow same-site paths; anything else (absolute URL, protocol-
    relative //host) would let a crafted login link bounce users elsewhere."""
    if next.startswith("/") and not next.startswith("//"):
        return next
    return "/"


def _signup_error(request: Request, errors, email: str):
    return templates.TemplateResponse(
        request, "signup.html", {"errors": errors, "form": {"email": email}}, status_code=422
    )


def _login_error(request: Request, errors, email: str, next: str):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"errors": errors, "form": {"email": email}, "next": next},
        status_code=422,
    )
