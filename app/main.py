from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, SessionLocal, engine, upgrade_schema
from app.models import Business
from app.routes import business, drafts, reviews

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="ReviewReply")

Base.metadata.create_all(bind=engine)
upgrade_schema()

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(business.router)
app.include_router(reviews.router)
app.include_router(drafts.router)


@app.get("/")
def index():
    db = SessionLocal()
    try:
        first_business = db.query(Business).order_by(Business.id).first()
    finally:
        db.close()

    if first_business is None:
        return RedirectResponse(url="/setup")
    return RedirectResponse(url=f"/businesses/{first_business.id}/dashboard")
