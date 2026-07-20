from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ApiSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class EmailDraftRequest(ApiSchema):
    lab_id: str = Field(min_length=1, max_length=120)
    language: Literal["en", "ko"] = "en"
    tone: Literal["polite", "enthusiastic", "concise"] = "polite"
    length: Literal["short", "standard", "detailed"] = "standard"
    purpose: Literal["graduate_application", "internship", "meeting"] = "graduate_application"
    additional_context: str = Field(default="", max_length=2000)


class GeneratedEmail(BaseModel):
    subject: str
    body: str
    personalization_notes: list[str] = Field(default_factory=list)


class EmailDraftResponse(ApiSchema):
    lab_id: str
    subject: str
    body: str
    personalization_notes: list[str]
    generation_mode: Literal["ai", "demo", "local_rule_based"]
    model: str | None


class EmailReviewRequest(ApiSchema):
    lab_id: str = Field(min_length=1, max_length=120)
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=10_000)
    language: Literal["en", "ko"] = "en"


class EmailReviewIssue(ApiSchema):
    category: Literal["spelling", "flow", "professor_fit"]
    severity: Literal["info", "warning"]
    message: str
    suggestion: str


class EmailReviewResponse(ApiSchema):
    score: int = Field(ge=0, le=100)
    summary: str
    issues: list[EmailReviewIssue]
    reviewed_subject: str
    reviewed_body: str
    review_mode: Literal["local_rule_based"] = "local_rule_based"
