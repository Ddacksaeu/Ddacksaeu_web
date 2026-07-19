from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RecommendationScorePart(BaseModel):
    score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    raw_score: float = Field(ge=0, le=100)
    available: bool


class EvidenceItem(BaseModel):
    type: str
    text: str


class RecommendationResponse(BaseModel):
    lab_id: str
    lab_name: str
    professor_name: str
    university: str
    department: str
    total_score: float = Field(ge=0, le=100)
    matched_keywords: list[str]
    missing_keywords: list[str]
    score_breakdown: dict[str, RecommendationScorePart]
    evidence: list[EvidenceItem]
    short_reason: str
    recommended_action: str
    data_completeness: float = Field(ge=0, le=1)
    warnings: list[str]
    data_origin: str
    calculated_at: datetime


class RecommendationListResponse(BaseModel):
    items: list[RecommendationResponse]
