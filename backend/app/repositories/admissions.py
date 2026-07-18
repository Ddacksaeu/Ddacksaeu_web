from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import AdmissionEvent


def list_admission_events(
    session: Session,
    *,
    start: datetime | None,
    end: datetime | None,
    university_id: str | None,
    department_id: str | None,
    event_type: str | None,
) -> list[AdmissionEvent]:
    statement: Select[tuple[AdmissionEvent]] = select(AdmissionEvent)
    if start is not None:
        statement = statement.where(AdmissionEvent.start_at >= start)
    if end is not None:
        statement = statement.where(AdmissionEvent.start_at < end)
    if university_id is not None:
        statement = statement.where(AdmissionEvent.university_id == university_id)
    if department_id is not None:
        statement = statement.where(AdmissionEvent.department_id == department_id)
    if event_type is not None:
        statement = statement.where(AdmissionEvent.event_type == event_type)
    return list(session.scalars(statement.order_by(AdmissionEvent.start_at, AdmissionEvent.id)))
