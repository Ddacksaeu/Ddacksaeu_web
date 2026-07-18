from datetime import UTC, datetime, timedelta

from app.models import AdmissionEvent

DEADLINE_IMMINENT_DAYS = 14


def event_status(event: AdmissionEvent, now: datetime) -> tuple[bool, bool]:
    end_at = event.end_at or event.start_at
    if end_at.tzinfo is None:
        end_at = end_at.replace(tzinfo=UTC)
    if event.start_at.tzinfo is None:
        start_at = event.start_at.replace(tzinfo=UTC)
    else:
        start_at = event.start_at
    is_ended = end_at < now
    is_deadline_imminent = (
        event.event_type == "application_deadline"
        and now <= start_at <= now + timedelta(days=DEADLINE_IMMINENT_DAYS)
    )
    return is_deadline_imminent, is_ended


def utc_now() -> datetime:
    return datetime.now(UTC)
