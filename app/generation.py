from typing import List, Optional

from anthropic import Anthropic

from app.config import settings
from app.models import Review, VoiceProfile

MODEL = "claude-sonnet-5"
MAX_TOKENS = 400

_client: Optional[Anthropic] = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def build_prompt(
    review: Review,
    voice_profile: VoiceProfile,
    recent_openings: Optional[List[str]] = None,
) -> dict:
    """Pure function: builds the {system, messages} payload for the Anthropic call."""
    recent_openings = recent_openings or []
    return {
        "system": _build_system_prompt(voice_profile, recent_openings),
        "messages": [{"role": "user", "content": _build_user_message(review)}],
    }


def _build_system_prompt(voice_profile: VoiceProfile, recent_openings: List[str]) -> str:
    phrases_to_use = _split_csv(voice_profile.phrases_to_use)
    phrases_to_avoid = _split_csv(voice_profile.phrases_to_avoid)
    examples = _split_lines(voice_profile.example_responses)[:5]

    lines = [
        "You are drafting a reply to a Google review on behalf of a small business owner.",
        "",
        f"Business type: {voice_profile.business.business_type}",
        f"Owner name: {voice_profile.business.owner_name}",
        f"Tone: {voice_profile.tone}",
        f"Sign-off to use: {voice_profile.sign_off}",
    ]

    if phrases_to_use:
        lines.append(f"Phrases the owner likes to use: {', '.join(phrases_to_use)}")
    if phrases_to_avoid:
        lines.append(f"Phrases to avoid: {', '.join(phrases_to_avoid)}")

    if examples:
        lines.append("")
        lines.append(
            "Examples of the owner's actual past responses (match this voice closely; "
            "weight these more heavily than the tone/phrase settings above):"
        )
        lines.extend(f"- {example}" for example in examples)

    if recent_openings:
        lines.append("")
        lines.append(
            "Do not open the reply the same way as these recently generated openings "
            "(vary your first sentence):"
        )
        lines.extend(f"- {opening}" for opening in recent_openings)

    lines.extend(
        [
            "",
            "Hard rules:",
            "- Reference at least one concrete detail from the review body.",
            "- Match the tone and use the sign-off given above.",
            "- If the rating is 1 or 2 stars, include an apology, a concrete remedy, and an "
            "invitation to contact the business directly. Do not invent a phone number, "
            "email address, or any other contact detail.",
            "- Never invent facts about the customer's visit beyond what the review states.",
            "- Write 2-5 sentences.",
        ]
    )

    return "\n".join(lines)


def _build_user_message(review: Review) -> str:
    lines = [
        "Write a reply to this review:",
        "",
        f"Author: {review.author_name}",
        f"Rating: {review.rating}/5",
    ]
    if review.review_date:
        lines.append(f"Date: {review.review_date.isoformat()}")
    lines.append(f"Review: {review.body}")
    return "\n".join(lines)


def _split_csv(raw: Optional[str]) -> List[str]:
    return [p.strip() for p in (raw or "").split(",") if p.strip()]


def _split_lines(raw: Optional[str]) -> List[str]:
    return [line.strip() for line in (raw or "").splitlines() if line.strip()]


def generate_reply(
    review: Review,
    voice_profile: VoiceProfile,
    recent_openings: Optional[List[str]] = None,
) -> str:
    prompt = build_prompt(review, voice_profile, recent_openings)
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=prompt["system"],
        messages=prompt["messages"],
    )
    return response.content[0].text.strip()
