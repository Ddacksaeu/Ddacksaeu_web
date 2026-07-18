from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from app.models import AdmissionEvent
from app.services.admissions import event_status
from scripts.seed import seed_database


def _seed(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        seed_database(session)


def test_admission_filters_and_order(client, session_factory) -> None:
    _seed(session_factory)
    response = client.get(
        "/api/v1/admissions", params={"university_id": "fixture-kaist", "event_type": "interview"}
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["fixture-kaist-admission-event"]
    assert response.json()["items"][0]["is_estimated"] is True
    assert (
        client.get(
            "/api/v1/admissions",
            params={"start_at": "2026-08-01T00:00:00Z", "end_at": "2026-09-01T00:00:00Z"},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/admissions", params={"event_type": "bad"}).status_code == 422


def test_admission_empty_and_ics_escaping(client, session_factory) -> None:
    _seed(session_factory)
    with session_factory() as session:
        event = session.get(AdmissionEvent, "fixture-kaist-admission-event")
        assert event is not None
        event.title = "한글, 특수;문자"
        event.description = "첫 줄\\둘째 줄"
        session.commit()
    assert (
        client.get("/api/v1/admissions", params={"university_id": "missing"}).json()["items"] == []
    )
    response = client.get("/api/v1/admissions/export.ics")
    assert response.headers["content-type"].startswith("text/calendar")
    assert "SUMMARY:한글\\, 특수\\;문자" in response.text
    assert "DESCRIPTION:첫 줄\\\\둘째 줄" in response.text


def test_deadline_status_uses_injected_now(session_factory) -> None:
    _seed(session_factory)
    with session_factory() as session:
        event = session.get(AdmissionEvent, "fixture-snu-admission-event")
        assert event is not None
        imminent, ended = event_status(event, datetime(2026, 8, 10, tzinfo=UTC))
        assert imminent is True
        assert ended is False
        _, ended = event_status(event, datetime(2026, 9, 1, tzinfo=UTC))
        assert ended is True
