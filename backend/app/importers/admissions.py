from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import AdmissionEvent, University

EVENT_TYPES = {"application_deadline", "interview", "schedule"}


@dataclass
class AdmissionImportReport:
    created: int = 0
    updated: int = 0
    skipped: list[dict[str, str]] = field(default_factory=list)


def _url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value.strip())
    return value.strip() if parsed.scheme in {"http", "https"} and parsed.netloc else None


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def import_admissions(
    session: Session, path: Path, *, dry_run: bool = False
) -> AdmissionImportReport:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise ValueError("admissions JSON must contain an events array")
    report = AdmissionImportReport()
    for index, item in enumerate(payload["events"], start=1):
        record = item if isinstance(item, dict) else {}
        identifier = record.get("id") if isinstance(record.get("id"), str) else f"events[{index}]"
        source_url, verified_at = (
            _url(record.get("source_url")),
            _timestamp(record.get("checked_at")),
        )
        start_at, end_at = (
            _timestamp(record.get("start_at")),
            _timestamp(record.get("end_at")) if record.get("end_at") else None,
        )
        event_type = record.get("event_type")
        university_id, university_name = record.get("university_id"), record.get("university_name")
        if not all(
            (
                isinstance(identifier, str) and identifier.strip(),
                isinstance(record.get("title"), str) and record["title"].strip(),
                source_url,
                verified_at,
                start_at,
                isinstance(university_id, str) and university_id.strip(),
                isinstance(university_name, str) and university_name.strip(),
            )
        ):
            report.skipped.append(
                {
                    "record": str(identifier),
                    "reason": (
                        "missing required id, title, university, source_url, "
                        "checked_at, or start_at"
                    ),
                }
            )
            continue
        if event_type not in EVENT_TYPES:
            report.skipped.append({"record": identifier, "reason": "invalid event_type"})
            continue
        if end_at and end_at < start_at:
            report.skipped.append({"record": identifier, "reason": "end_at is before start_at"})
            continue
        if dry_run:
            if session.get(AdmissionEvent, identifier):
                report.updated += 1
            else:
                report.created += 1
            continue
        university = session.get(University, university_id)
        if university is None:
            university = University(
                id=university_id,
                name=university_name,
                source_url=source_url,
                source_checked_at=verified_at,
            )
            session.add(university)
            # AdmissionEvent has no ORM relationship to University, so flush the
            # new foreign-key target before adding its first event.
            session.flush()
        event = session.get(AdmissionEvent, identifier)
        values = {
            "university_id": university_id,
            "department_id": None,
            "title": record["title"].strip(),
            "event_type": event_type,
            "start_at": start_at,
            "end_at": end_at,
            "application_url": _url(record.get("application_url")),
            "description": record.get("description")
            if isinstance(record.get("description"), str)
            else None,
            "is_estimated": bool(record.get("is_estimated", False)),
            "source_url": source_url,
            "last_verified_at": verified_at,
            "origin": "official_import",
        }
        if event is None:
            session.add(AdmissionEvent(id=identifier, **values))
            report.created += 1
        else:
            for key, value in values.items():
                setattr(event, key, value)
            report.updated += 1
    return report
