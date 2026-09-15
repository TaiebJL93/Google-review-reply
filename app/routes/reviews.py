from typing import List

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import current_user, get_owned_business
from app.database import get_db
from app.models import Review, User
from app.sources.base import ReviewData
from app.sources.csv_source import CsvSource, CsvSourceError
from app.sources.manual_source import ManualSource, ManualSourceError
from app.templating import templates

router = APIRouter()


@router.get("/businesses/{business_id}/dashboard")
def dashboard(
    request: Request,
    business_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    business = get_owned_business(db, user, business_id)
    reviews = (
        db.query(Review)
        .filter(Review.business_id == business_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        request, "dashboard.html", {"business": business, "reviews": reviews}
    )


@router.get("/businesses/{business_id}/import")
def import_form(
    request: Request,
    business_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    business = get_owned_business(db, user, business_id)
    return templates.TemplateResponse(
        request, "import_reviews.html", {"business": business, "errors": []}
    )


@router.post("/businesses/{business_id}/import/csv")
async def import_csv(
    request: Request,
    business_id: int,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    business = get_owned_business(db, user, business_id)
    content = await file.read()
    try:
        reviews_data = CsvSource(content).fetch()
    except CsvSourceError as exc:
        return templates.TemplateResponse(
            request,
            "import_reviews.html",
            {"business": business, "errors": [str(exc)]},
            status_code=422,
        )

    _persist_reviews(db, business_id, reviews_data, source="csv")
    return RedirectResponse(url=f"/businesses/{business_id}/dashboard", status_code=303)


@router.post("/businesses/{business_id}/import/manual")
def import_manual(
    request: Request,
    business_id: int,
    text: str = Form(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    business = get_owned_business(db, user, business_id)
    try:
        reviews_data = ManualSource(text).fetch()
    except ManualSourceError as exc:
        return templates.TemplateResponse(
            request,
            "import_reviews.html",
            {"business": business, "errors": [str(exc)]},
            status_code=422,
        )

    _persist_reviews(db, business_id, reviews_data, source="manual")
    return RedirectResponse(url=f"/businesses/{business_id}/dashboard", status_code=303)


def _persist_reviews(db: Session, business_id: int, reviews_data: List[ReviewData], source: str) -> None:
    for data in reviews_data:
        db.add(
            Review(
                business_id=business_id,
                source=source,
                author_name=data.author_name,
                rating=data.rating,
                body=data.body,
                review_date=data.review_date,
            )
        )
    db.commit()
