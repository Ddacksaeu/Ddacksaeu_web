from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.repositories.admissions import list_admission_events
from app.schemas.admissions import AdmissionEventResponse, AdmissionListResponse
from app.services.admissions import event_status, utc_now

router = APIRouter(prefix="/admissions", tags=["admissions"])


def _response(event, now: datetime) -> AdmissionEventResponse:
    imminent, ended = event_status(event, now)
    return AdmissionEventResponse.model_validate(
        {
            "id": event.id,
            "university_id": event.university_id,
            "department_id": event.department_id,
            "title": event.title,
            "event_type": event.event_type,
            "start_at": event.start_at,
            "end_at": event.end_at,
            "application_url": event.application_url,
            "description": event.description,
            "is_estimated": event.is_estimated,
            "source_url": event.source_url,
            "last_verified_at": event.last_verified_at,
            "is_deadline_imminent": imminent,
            "is_ended": ended,
        }
    )


def _events(session, start_at, end_at, university_id, department_id, event_type):
    return list_admission_events(
        session,
        start=start_at,
        end=end_at,
        university_id=university_id,
        department_id=department_id,
        event_type=event_type,
    )


@router.get("", response_model=AdmissionListResponse)
def list_admissions(
    session: Annotated[Session, Depends(get_db_session)],
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    university_id: str | None = None,
    department_id: str | None = None,
    event_type: Annotated[
        str | None, Query(pattern="^(application_deadline|interview|schedule)$")
    ] = None,
) -> AdmissionListResponse:
    if start_at and end_at and start_at >= end_at:
        raise HTTPException(status_code=422, detail="end_at must be after start_at")
    now = utc_now()
    return AdmissionListResponse(
        items=[
            _response(event, now)
            for event in _events(
                session, start_at, end_at, university_id, department_id, event_type
            )
        ]
    )


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _stamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


@router.get("/export.ics")
def export_ics(
    session: Annotated[Session, Depends(get_db_session)],
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    university_id: str | None = None,
    department_id: str | None = None,
    event_type: Annotated[
        str | None, Query(pattern="^(application_deadline|interview|schedule)$")
    ] = None,
) -> Response:
    now = utc_now()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Ddacksaeu//Admission Fixtures//EN",
        "CALSCALE:GREGORIAN",
    ]
    for event in _events(session, start_at, end_at, university_id, department_id, event_type):
        description = event.description or ""
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{event.id}@ddacksaeu.fixture",
                f"DTSTAMP:{_stamp(now)}",
                f"DTSTART:{_stamp(event.start_at)}",
                f"DTEND:{_stamp(event.end_at or event.start_at)}",
                f"SUMMARY:{_escape(event.title)}",
                f"DESCRIPTION:{_escape(description)}",
                f"URL:{_escape(event.application_url or event.source_url)}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return Response("\r\n".join(lines) + "\r\n", media_type="text/calendar; charset=utf-8")
