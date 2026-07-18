from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ApiSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class LabListItem(ApiSchema):
    id: str
    name: str
    professor_name: str
    university: str
    department: str
    field: str
    summary: str | None
    keywords: list[str]
    homepage_url: str | None
    updated_at: datetime
    recommendation_score: int | None
    is_favorite: bool


class LabSearchResponse(ApiSchema):
    items: list[LabListItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)


class SimilarLabsResponse(ApiSchema):
    items: list[LabListItem]


class LabFactResponse(ApiSchema):
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    fact_type: str
    value_text: str | None
    value_number: int | None
    audience: str | None
    origin: str
    source_url: str | None
    source_checked_at: datetime | None


class PaperResponse(ApiSchema):
    id: str
    title: str
    venue: str
    published_year: int
    abstract: str | None
    summary: str | None
    keywords: list[str]
    paper_url: str | None
    source_url: str | None
    source_checked_at: datetime | None


class LabDetail(LabListItem):
    location: str | None
    contact_email: str | None
    source_url: str | None
    source_checked_at: datetime | None
    facts: list[LabFactResponse]
    papers: list[PaperResponse]
