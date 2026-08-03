from datetime import date

from app.generation import build_prompt
from app.models import Business, Review, VoiceProfile


def _make_review_and_profile(**overrides):
    business = Business(name="Java Hut", business_type="coffee shop", owner_name="Maria Ortiz")
    voice_profile = VoiceProfile(
        business=business,
        tone="warm",
        sign_off="Warm regards, Maria",
        phrases_to_use="thank you, appreciate",
        phrases_to_avoid="whatever",
        example_responses="Thanks so much for stopping by, we loved having you!",
    )
    defaults = dict(
        business=business,
        source="manual",
        author_name="Jane Doe",
        rating=5,
        body="Loved the oat milk latte and the quick service.",
        review_date=date(2024, 5, 2),
    )
    defaults.update(overrides)
    review = Review(**defaults)
    return review, voice_profile


def test_prompt_includes_review_specifics():
    review, voice_profile = _make_review_and_profile()
    prompt = build_prompt(review, voice_profile)

    user_message = prompt["messages"][0]["content"]
    assert "Jane Doe" in user_message
    assert "5/5" in user_message
    assert "oat milk latte" in user_message
    assert "2024-05-02" in user_message


def test_prompt_includes_voice_attributes():
    review, voice_profile = _make_review_and_profile()
    system = build_prompt(review, voice_profile)["system"]

    assert "coffee shop" in system
    assert "Maria Ortiz" in system
    assert "warm" in system
    assert "Warm regards, Maria" in system
    assert "thank you" in system
    assert "whatever" in system
    assert "Thanks so much for stopping by" in system


def test_system_prompt_always_includes_low_rating_rule():
    review, voice_profile = _make_review_and_profile()
    system = build_prompt(review, voice_profile)["system"]

    assert "apology" in system
    assert "concrete remedy" in system
    assert "invitation to contact" in system


def test_recent_openings_are_included_with_avoidance_instruction():
    review, voice_profile = _make_review_and_profile()
    system = build_prompt(review, voice_profile, recent_openings=["Thank you so much"])["system"]

    assert "Thank you so much" in system
    assert "Do not open the reply the same way" in system


def test_no_examples_omits_examples_section():
    review, voice_profile = _make_review_and_profile()
    voice_profile.example_responses = ""

    system = build_prompt(review, voice_profile)["system"]
    assert "Examples of the owner's actual past responses" not in system
