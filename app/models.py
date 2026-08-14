from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    business_type = Column(String, nullable=False)
    owner_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    voice_profile = relationship(
        "VoiceProfile", back_populates="business", uselist=False, cascade="all, delete-orphan"
    )
    reviews = relationship("Review", back_populates="business", cascade="all, delete-orphan")


class VoiceProfile(Base):
    __tablename__ = "voice_profiles"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, unique=True)
    tone = Column(String, nullable=False)  # "warm" | "professional" | "casual"
    sign_off = Column(String, nullable=False)
    phrases_to_use = Column(Text, default="")
    phrases_to_avoid = Column(Text, default="")
    example_responses = Column(Text, default="")  # newline-delimited, up to 5 used

    business = relationship("Business", back_populates="voice_profile")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    source = Column(String, nullable=False)  # "csv" | "manual" | "google"
    author_name = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    body = Column(Text, nullable=False)
    review_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    business = relationship("Business", back_populates="reviews")
    draft = relationship("Draft", back_populates="review", uselist=False, cascade="all, delete-orphan")


class Draft(Base):
    __tablename__ = "drafts"
    __table_args__ = (UniqueConstraint("review_id", name="uq_draft_review_id"),)

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False)
    content = Column(Text, nullable=False)
    saved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    review = relationship("Review", back_populates="draft")
