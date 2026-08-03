import pytest
from pydantic import ValidationError

from app.schemas import VoiceProfileForm


def test_valid_profile():
    profile = VoiceProfileForm(
        tone="warm",
        sign_off="Warm regards, Maria",
        phrases_to_use="thank you, appreciate",
        phrases_to_avoid="unfortunately",
        example_responses="Thanks so much!\nWe appreciate you stopping by.",
    )
    assert profile.tone == "warm"


def test_invalid_tone_raises():
    with pytest.raises(ValidationError):
        VoiceProfileForm(tone="sarcastic", sign_off="Maria")


def test_blank_sign_off_raises():
    with pytest.raises(ValidationError):
        VoiceProfileForm(tone="warm", sign_off="   ")


def test_too_many_example_responses_raises():
    examples = "\n".join(f"Example {i}" for i in range(6))
    with pytest.raises(ValidationError, match="at most 5"):
        VoiceProfileForm(tone="warm", sign_off="Maria", example_responses=examples)


def test_exactly_five_examples_ok():
    examples = "\n".join(f"Example {i}" for i in range(5))
    profile = VoiceProfileForm(tone="warm", sign_off="Maria", example_responses=examples)
    assert profile.example_responses == examples
