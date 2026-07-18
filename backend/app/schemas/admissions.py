from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdmissionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    university_id: str | None
    department_id: str | None
    title: str
    event_type: str
    start_at: datetime
    end_at: datetime | None
    application_url: str | None
    description: str | None
    is_estimated: bool
    source_url: str
    last_verified_at: datetime | None
    is_deadline_imminent: bool
    is_ended: bool


class AdmissionListResponse(BaseModel):
    items: list[AdmissionEventResponse]
