from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import current_user, get_owned_business
from app.database import get_db
from app.models import Business, User, VoiceProfile
from app.schemas import BusinessCreate, VoiceProfileForm
from app.templating import templates

router = APIRouter()


@router.get("/setup")
def setup_form(request: Request, user: User = Depends(current_user)):
    return templates.TemplateResponse(request, "setup_business.html", {"errors": []})


@router.post("/businesses")
def create_business(
    request: Request,
    name: str = Form(...),
    business_type: str = Form(...),
    owner_name: str = Form(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    try:
        data = BusinessCreate(name=name, business_type=business_type, owner_name=owner_name)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "setup_business.html",
            {
                "errors": [e["msg"] for e in exc.errors()],
                "form": {"name": name, "business_type": business_type, "owner_name": owner_name},
            },
            status_code=422,
        )

    business = Business(
        user_id=user.id,
        name=data.name,
        business_type=data.business_type,
        owner_name=data.owner_name,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return RedirectResponse(url=f"/businesses/{business.id}/voice-setup", status_code=303)


@router.get("/businesses/{business_id}/voice-setup")
def voice_setup_form(
    request: Request,
    business_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    business = get_owned_business(db, user, business_id)
    return templates.TemplateResponse(
        request, "setup_voice.html", {"business": business, "errors": []}
    )


@router.post("/businesses/{business_id}/voice")
def save_voice_profile(
    request: Request,
    business_id: int,
    tone: str = Form(...),
    sign_off: str = Form(...),
    phrases_to_use: str = Form(""),
    phrases_to_avoid: str = Form(""),
    example_responses: str = Form(""),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    business = get_owned_business(db, user, business_id)
    try:
        data = VoiceProfileForm(
            tone=tone,
            sign_off=sign_off,
            phrases_to_use=phrases_to_use,
            phrases_to_avoid=phrases_to_avoid,
            example_responses=example_responses,
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "setup_voice.html",
            {"business": business, "errors": [e["msg"] for e in exc.errors()]},
            status_code=422,
        )

    profile = business.voice_profile
    if profile is None:
        profile = VoiceProfile(business_id=business.id)
        db.add(profile)

    profile.tone = data.tone
    profile.sign_off = data.sign_off
    profile.phrases_to_use = data.phrases_to_use
    profile.phrases_to_avoid = data.phrases_to_avoid
    profile.example_responses = data.example_responses
    db.commit()

    return RedirectResponse(url=f"/businesses/{business.id}/dashboard", status_code=303)
