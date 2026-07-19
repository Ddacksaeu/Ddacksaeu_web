from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ApiSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UserProfileResponse(ApiSchema):
    name: str
    affiliation: str
    status: str
    program: str
    interests: list[str]
    skills: list[str]
    methodologies: list[str]
    projects: list[str]
    updated_at: datetime


class UserProfileUpdate(ApiSchema):
    name: str | None = Field(default=None, max_length=120)
    affiliation: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, max_length=80)
    program: str | None = Field(default=None, max_length=120)
    interests: list[str] | None = Field(default=None, max_length=50)
    skills: list[str] | None = Field(default=None, max_length=50)
    methodologies: list[str] | None = Field(default=None, max_length=50)
    projects: list[str] | None = Field(default=None, max_length=50)


class FavoriteListResponse(ApiSchema):
    lab_ids: list[str]


EventKind = Literal["apply", "contact", "docs", "interview"]


class CalendarEventCreate(ApiSchema):
    title: str = Field(min_length=1, max_length=200)
    kind: EventKind
    date: date
    lab_id: str | None = Field(default=None, max_length=120)
    memo: str | None = Field(default=None, max_length=2_000)


class CalendarEventUpdate(ApiSchema):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    kind: EventKind | None = None
    date: date | None = None
    lab_id: str | None = Field(default=None, max_length=120)
    memo: str | None = Field(default=None, max_length=2_000)


class CalendarEventResponse(CalendarEventCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class CalendarEventListResponse(ApiSchema):
    items: list[CalendarEventResponse]
