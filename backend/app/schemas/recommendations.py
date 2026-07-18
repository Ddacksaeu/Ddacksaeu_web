from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RecommendationScorePart(BaseModel):
    score: int = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    contribution: float = Field(ge=0, le=100)
    unavailable: bool = False
    degraded: bool = False


class RecommendationResponse(BaseModel):
    lab_id: str
    lab_name: str
    professor_name: str
    university: str
    department: str
    total_score: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    matched_keywords: list[str]
    missing_keywords: list[str]
    user_keyword_weights: dict[str, float]
    score_breakdown: dict[str, RecommendationScorePart]
    evidence: dict[str, Any]
    short_reason: str
    recommended_action: str
    calculated_at: datetime


class RecommendationListResponse(BaseModel):
    items: list[RecommendationResponse]
