from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


def new_id() -> str:
    return str(uuid4())


class TimestampedModel:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class User(TimestampedModel, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile: Mapped[UserProfile | None] = relationship(back_populates="user", uselist=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    affiliation: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    program: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    interests_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    skills_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    methodologies_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    projects_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="profile")


class Lab(TimestampedModel, Base):
    __tablename__ = "labs"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    professor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str] = mapped_column(String(200), nullable=False)
    field: Mapped[str] = mapped_column(String(120), nullable=False)
    homepage_url: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(320))
    summary_text: Mapped[str | None] = mapped_column(Text)
    summary_origin: Mapped[str] = mapped_column(String(32), default="fixture", nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    facts: Mapped[list[LabFact]] = relationship(back_populates="lab", cascade="all, delete-orphan")
    papers: Mapped[list[Paper]] = relationship(back_populates="lab", cascade="all, delete-orphan")


class LabFact(Base):
    __tablename__ = "lab_facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    lab_id: Mapped[str] = mapped_column(ForeignKey("labs.id"), nullable=False, index=True)
    fact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text)
    value_number: Mapped[int | None] = mapped_column(Integer)
    audience: Mapped[str | None] = mapped_column(String(32))
    origin: Mapped[str] = mapped_column(String(32), default="fixture", nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lab: Mapped[Lab] = relationship(back_populates="facts")


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    lab_id: Mapped[str] = mapped_column(ForeignKey("labs.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    venue: Mapped[str] = mapped_column(String(200), nullable=False)
    published_year: Mapped[int] = mapped_column(Integer, nullable=False)
    keywords_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    paper_url: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lab: Mapped[Lab] = relationship(back_populates="papers")


class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    lab_id: Mapped[str] = mapped_column(ForeignKey("labs.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class CalendarEvent(TimestampedModel, Base):
    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    memo: Mapped[str | None] = mapped_column(Text)
    lab_id: Mapped[str | None] = mapped_column(ForeignKey("labs.id"))


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class DocumentAnalysis(Base):
    __tablename__ = "document_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("uploaded_documents.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    keywords_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    skills_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    methodologies_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    projects_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    completeness: Mapped[int | None] = mapped_column(Integer)
    analysis_origin: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(String(100))
