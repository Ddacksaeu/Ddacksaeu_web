from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator


class EducationAnalysis(BaseModel):
    degree: str = Field(default="", max_length=300)
    institution: str = Field(default="", max_length=300)
    location: str = Field(default="", max_length=200)
    start_date: str = Field(default="", max_length=100)
    end_date: str = Field(default="", max_length=100)
    details: list[str] = Field(default_factory=list)


class ExperienceAnalysis(BaseModel):
    title: str = Field(default="", max_length=300)
    organization: str = Field(default="", max_length=300)
    location: str = Field(default="", max_length=200)
    start_date: str = Field(default="", max_length=100)
    end_date: str = Field(default="", max_length=100)
    details: list[str] = Field(default_factory=list)


class ProjectAnalysis(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    organization: str = Field(default="", max_length=300)
    location: str = Field(default="", max_length=200)
    start_date: str = Field(default="", max_length=100)
    end_date: str = Field(default="", max_length=100)

    description: str = Field(default="", max_length=2_000)
    details: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    value: str
    confidence: float = Field(ge=0, le=1)
    evidence: str


class CategoryFeedback(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    current_state: str = Field(min_length=1, max_length=1_000)
    improvements: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class StructuredDocumentAnalysis(BaseModel):
    education: list[EducationAnalysis] = Field(default_factory=list)

    work_experience: list[ExperienceAnalysis] = Field(
        default_factory=list
    )

    campus_community_involvement: list[ExperienceAnalysis] = Field(
        default_factory=list
    )

    research_experience: list[ExperienceAnalysis] = Field(
        default_factory=list
    )

    projects: list[ProjectAnalysis] = Field(default_factory=list)

    skills: list[str] = Field(default_factory=list)
    research_interests: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)

    keyword_weights: dict[
        str,
        Annotated[float, Field(ge=0, le=1)],
    ] = Field(default_factory=dict)

    short_summary: str = Field(
        default="Resume analysis completed.",
        min_length=1,
        max_length=2_000,
    )

    evidence_items: dict[str, list[EvidenceItem]] = Field(
        default_factory=dict
    )

    category_feedback: list[CategoryFeedback] = Field(
        default_factory=list
    )

    @field_validator("education", mode="before")
    @classmethod
    def upgrade_legacy_education(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [
                {"degree": item} if isinstance(item, str) else item
                for item in value
            ]
        return value

    @field_validator(
        "work_experience",
        "research_experience",
        "campus_community_involvement",
        mode="before",
    )
    @classmethod
    def upgrade_legacy_experience(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [
                {"title": item} if isinstance(item, str) else item
                for item in value
            ]
        return value


class DocumentAnalysisResponse(StructuredDocumentAnalysis):
    document_id: str
    analysis_id: str
    status: str = "completed"

    analyzer_origin: str = "local_rule_based"

    original_filename: str | None = None
    file_type: str | None = None
    file_size: int | None = None

    warnings: list[str] = Field(default_factory=list)
