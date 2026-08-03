from typing import Literal

from pydantic import BaseModel, field_validator

MAX_EXAMPLE_RESPONSES = 5


class BusinessCreate(BaseModel):
    name: str
    business_type: str
    owner_name: str

    @field_validator("name", "business_type", "owner_name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field is required.")
        return v


class VoiceProfileForm(BaseModel):
    tone: Literal["warm", "professional", "casual"]
    sign_off: str
    phrases_to_use: str = ""
    phrases_to_avoid: str = ""
    example_responses: str = ""

    @field_validator("sign_off")
    @classmethod
    def sign_off_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Sign-off is required.")
        return v

    @field_validator("example_responses")
    @classmethod
    def limit_examples(cls, v: str) -> str:
        lines = [line for line in v.splitlines() if line.strip()]
        if len(lines) > MAX_EXAMPLE_RESPONSES:
            raise ValueError(f"Provide at most {MAX_EXAMPLE_RESPONSES} example responses.")
        return v
