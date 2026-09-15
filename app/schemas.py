import re
from typing import Literal

from pydantic import BaseModel, field_validator

MAX_EXAMPLE_RESPONSES = 5
MIN_PASSWORD_LENGTH = 8

# Deliberately loose: one "@" with something on each side and a dot in the
# domain. Real validation happens when the person tries to use the address;
# a strict RFC regex mostly just rejects valid-but-unusual addresses.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(v: str) -> str:
    v = v.strip().lower()
    if not _EMAIL_RE.match(v):
        raise ValueError("Enter a valid email address.")
    return v


class SignupForm(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        return _normalize_email(v)

    @field_validator("password")
    @classmethod
    def strong_enough(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        return v


class LoginForm(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        return _normalize_email(v)

    @field_validator("password")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v:
            raise ValueError("Password is required.")
        return v


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
