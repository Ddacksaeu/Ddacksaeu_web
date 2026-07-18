from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ApiSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class EmailDraftRequest(ApiSchema):
    lab_id: str = Field(min_length=1, max_length=120)
    user_id: str = Field(default="demo-user", min_length=1, max_length=64)
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
    generation_mode: Literal["ai", "demo"]
    model: str | None
