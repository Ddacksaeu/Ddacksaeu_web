from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RecommendationScores(BaseModel):
    keyword_score: int = Field(ge=0, le=100)
    semantic_score: int = Field(ge=0, le=100)
    research_score: int = Field(ge=0, le=100)
    preference_score: int = Field(ge=0, le=100)
    total_score: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)


class RecommendationRecord(RecommendationScores):
    user_id: str
    lab_id: str
    reason: str
    score_breakdown: dict[str, Any] = Field(default_factory=dict)


class CrawlRunRecord(BaseModel):
    source_id: str
    status: Literal["pending", "running", "succeeded", "failed"]
    started_at: datetime
    completed_at: datetime | None = None
    discovered_count: int = Field(default=0, ge=0)
    saved_count: int = Field(default=0, ge=0)
    error_message: str | None = None
