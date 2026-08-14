from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.generation import generate_reply
from app.models import Draft, Review
from app.templating import templates

router = APIRouter()

RECENT_OPENINGS_COUNT = 3
OPENING_WORD_COUNT = 6


@router.post("/reviews/{review_id}/draft")
def create_draft(request: Request, review_id: int, db: Session = Depends(get_db)):
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")

    voice_profile = review.business.voice_profile
    if voice_profile is None:
        raise HTTPException(
            status_code=400,
            detail="Set up a voice profile for this business before drafting replies.",
        )

    recent_openings = _recent_openings(db, review.business_id, exclude_review_id=review.id)
    content = generate_reply(review, voice_profile, recent_openings)

    draft = review.draft
    if draft is None:
        draft = Draft(review_id=review.id, content=content)
        db.add(draft)
    else:
        draft.content = content
        draft.saved_at = None
    db.commit()
    db.refresh(draft)

    return templates.TemplateResponse(
        request, "_draft_partial.html", {"review": review, "draft": draft}
    )


@router.post("/reviews/{review_id}/draft/save")
def save_draft(
    request: Request,
    review_id: int,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")

    draft = review.draft
    if draft is None:
        raise HTTPException(status_code=400, detail="Generate a draft before saving.")

    content = content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Draft content cannot be empty.")

    draft.content = content
    draft.saved_at = datetime.utcnow()
    db.commit()
    db.refresh(draft)

    return templates.TemplateResponse(
        request, "_draft_partial.html", {"review": review, "draft": draft}
    )


def _recent_openings(db: Session, business_id: int, exclude_review_id: int) -> List[str]:
    drafts = (
        db.query(Draft)
        .join(Review, Draft.review_id == Review.id)
        .filter(Review.business_id == business_id, Review.id != exclude_review_id)
        .order_by(desc(Draft.created_at))
        .limit(RECENT_OPENINGS_COUNT)
        .all()
    )
    return [" ".join(draft.content.split()[:OPENING_WORD_COUNT]) for draft in drafts]
