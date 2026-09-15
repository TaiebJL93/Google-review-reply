from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.auth import LoginRequired, current_user
from app.config import settings
from app.database import Base, engine, get_db, upgrade_schema
from app.models import Business, User
from app.routes import auth, business, drafts, google_auth, reviews

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="ReviewReply")

Base.metadata.create_all(bind=engine)
upgrade_schema()

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=settings.secure_cookies,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(auth.router)
app.include_router(business.router)
app.include_router(reviews.router)
app.include_router(drafts.router)
app.include_router(google_auth.router)


@app.exception_handler(LoginRequired)
def redirect_to_login(request: Request, exc: LoginRequired):
    """Send signed-out visitors to the login page, remembering where they
    were headed so a successful login lands them back there."""
    target = request.url.path
    if request.url.query:
        target = f"{target}?{request.url.query}"
    if target == "/":
        return RedirectResponse(url="/login", status_code=303)
    return RedirectResponse(url=f"/login?next={quote(target, safe='')}", status_code=303)


@app.get("/healthz")
def healthz():
    """Render polls this to know the service is up; keep it dependency-free."""
    return {"status": "ok"}


@app.get("/")
def index(user: User = Depends(current_user), db: Session = Depends(get_db)):
    first_business = (
        db.query(Business).filter(Business.user_id == user.id).order_by(Business.id).first()
    )
    if first_business is None:
        return RedirectResponse(url="/setup")
    return RedirectResponse(url=f"/businesses/{first_business.id}/dashboard")
