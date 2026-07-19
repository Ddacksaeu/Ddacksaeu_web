from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class ProjectAnalysis(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2_000)
    technologies: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    value: str
    confidence: float = Field(ge=0, le=1)
    evidence: str


class StructuredDocumentAnalysis(BaseModel):
    education: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[ProjectAnalysis] = Field(default_factory=list)
    research_experience: list[str] = Field(default_factory=list)
    research_interests: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    keyword_weights: dict[str, Annotated[float, Field(ge=0, le=1)]] = Field(default_factory=dict)
    short_summary: str = Field(min_length=1, max_length=2_000)
    evidence_items: dict[str, list[EvidenceItem]] = Field(default_factory=dict)


class DocumentAnalysisResponse(StructuredDocumentAnalysis):
    document_id: str
    analysis_id: str
    status: str = "completed"
    analyzer_origin: str = "local_rule_based"
    original_filename: str | None = None
    file_type: str | None = None
    file_size: int | None = None
    warnings: list[str] = Field(default_factory=list)
