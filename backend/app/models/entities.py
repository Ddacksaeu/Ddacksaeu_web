from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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


class University(TimestampedModel, Base):
    __tablename__ = "universities"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    country: Mapped[str] = mapped_column(String(80), default="KR", nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    departments: Mapped[list[Department]] = relationship(
        back_populates="university", cascade="all, delete-orphan"
    )
    professors: Mapped[list[Professor]] = relationship(
        back_populates="university", cascade="all, delete-orphan"
    )


class Department(TimestampedModel, Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("university_id", "name", name="uq_departments_university_name"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    university_id: Mapped[str] = mapped_column(
        ForeignKey("universities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    university: Mapped[University] = relationship(back_populates="departments")
    professors: Mapped[list[Professor]] = relationship(back_populates="department")
    admission_events: Mapped[list[AdmissionEvent]] = relationship(back_populates="department")


class Professor(TimestampedModel, Base):
    __tablename__ = "professors"
    __table_args__ = (
        UniqueConstraint("university_id", "name", name="uq_professors_university_name"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    university_id: Mapped[str] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    department_id: Mapped[str] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    profile_url: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    university: Mapped[University] = relationship(back_populates="professors")
    department: Mapped[Department] = relationship(back_populates="professors")
    labs: Mapped[list[Lab]] = relationship(back_populates="professor")


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    term_ko: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    term_en: Mapped[str | None] = mapped_column(String(200), unique=True)
    normalized_term: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)

    labs: Mapped[list[LabKeyword]] = relationship(
        back_populates="keyword", cascade="all, delete-orphan"
    )
    users: Mapped[list[UserKeyword]] = relationship(
        back_populates="keyword", cascade="all, delete-orphan"
    )


class User(TimestampedModel, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(500))
    profile: Mapped[UserProfile | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    keywords: Mapped[list[UserKeyword]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list[Recommendation]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    affiliation: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    program: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    interests_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    skills_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    methodologies_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    projects_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="profile")


class Lab(TimestampedModel, Base):
    __tablename__ = "labs"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    professor_id: Mapped[str] = mapped_column(
        ForeignKey("professors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
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

    professor: Mapped[Professor] = relationship(back_populates="labs")
    facts: Mapped[list[LabFact]] = relationship(back_populates="lab", cascade="all, delete-orphan")
    papers: Mapped[list[Paper]] = relationship(back_populates="lab", cascade="all, delete-orphan")
    keywords: Mapped[list[LabKeyword]] = relationship(
        back_populates="lab", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list[Recommendation]] = relationship(
        back_populates="lab", cascade="all, delete-orphan"
    )


class LabKeyword(Base):
    __tablename__ = "lab_keywords"

    lab_id: Mapped[str] = mapped_column(ForeignKey("labs.id", ondelete="CASCADE"), primary_key=True)
    keyword_id: Mapped[str] = mapped_column(
        ForeignKey("keywords.id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    lab: Mapped[Lab] = relationship(back_populates="keywords")
    keyword: Mapped[Keyword] = relationship(back_populates="labs")


class UserKeyword(Base):
    __tablename__ = "user_keywords"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    keyword_id: Mapped[str] = mapped_column(
        ForeignKey("keywords.id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="keywords")
    keyword: Mapped[Keyword] = relationship(back_populates="users")


class LabFact(Base):
    __tablename__ = "lab_facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    lab_id: Mapped[str] = mapped_column(
        ForeignKey("labs.id", ondelete="CASCADE"), nullable=False, index=True
    )
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
    __table_args__ = (UniqueConstraint("lab_id", "external_id", name="uq_papers_lab_external_id"),)

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    lab_id: Mapped[str] = mapped_column(
        ForeignKey("labs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    venue: Mapped[str] = mapped_column(String(200), nullable=False)
    published_year: Mapped[int] = mapped_column(Integer, nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(255))
    keywords_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    paper_url: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lab: Mapped[Lab] = relationship(back_populates="papers")


class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    lab_id: Mapped[str] = mapped_column(ForeignKey("labs.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class Recommendation(TimestampedModel, Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        UniqueConstraint("user_id", "lab_id", name="uq_recommendations_user_lab"),
        CheckConstraint("keyword_score BETWEEN 0 AND 100", name="ck_recommendations_keyword_score"),
        CheckConstraint(
            "semantic_score BETWEEN 0 AND 100", name="ck_recommendations_semantic_score"
        ),
        CheckConstraint(
            "research_score BETWEEN 0 AND 100", name="ck_recommendations_research_score"
        ),
        CheckConstraint(
            "preference_score BETWEEN 0 AND 100", name="ck_recommendations_preference_score"
        ),
        CheckConstraint("total_score BETWEEN 0 AND 100", name="ck_recommendations_total_score"),
        CheckConstraint("confidence BETWEEN 0 AND 100", name="ck_recommendations_confidence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lab_id: Mapped[str] = mapped_column(
        ForeignKey("labs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    keyword_score: Mapped[int] = mapped_column(Integer, nullable=False)
    semantic_score: Mapped[int] = mapped_column(Integer, nullable=False)
    research_score: Mapped[int] = mapped_column(Integer, nullable=False)
    preference_score: Mapped[int] = mapped_column(Integer, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped[User] = relationship(back_populates="recommendations")
    lab: Mapped[Lab] = relationship(back_populates="recommendations")


class CalendarEvent(TimestampedModel, Base):
    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    memo: Mapped[str | None] = mapped_column(Text)
    lab_id: Mapped[str | None] = mapped_column(ForeignKey("labs.id", ondelete="SET NULL"))


class AdmissionEvent(TimestampedModel, Base):
    __tablename__ = "admission_events"
    __table_args__ = (
        CheckConstraint(
            "university_id IS NOT NULL OR department_id IS NOT NULL",
            name="ck_admission_events_owner",
        ),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    university_id: Mapped[str | None] = mapped_column(
        ForeignKey("universities.id", ondelete="CASCADE"), index=True
    )
    department_id: Mapped[str | None] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    origin: Mapped[str] = mapped_column(String(32), default="fixture", nullable=False)

    department: Mapped[Department | None] = relationship(back_populates="admission_events")


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
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
        ForeignKey("uploaded_documents.id", ondelete="CASCADE"), nullable=False, index=True
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


class CrawlSource(TimestampedModel, Base):
    __tablename__ = "crawl_sources"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    lab_id: Mapped[str | None] = mapped_column(
        ForeignKey("labs.id", ondelete="SET NULL"), index=True
    )
    professor_id: Mapped[str | None] = mapped_column(
        ForeignKey("professors.id", ondelete="SET NULL"), index=True
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    runs: Mapped[list[CrawlRun]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class CrawlRun(Base):
    __tablename__ = "crawl_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')", name="ck_crawl_runs_status"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("crawl_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    saved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    source: Mapped[CrawlSource] = relationship(back_populates="runs")
