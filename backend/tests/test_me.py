from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from scripts.seed import seed_database


def test_profile_favorites_and_calendar_are_persisted(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        seed_database(session)

    profile = client.patch(
        "/api/v1/me/profile", json={"name": "Persisted User", "skills": ["Python"]}
    )
    assert profile.status_code == 200
    assert client.get("/api/v1/me/profile").json()["name"] == "Persisted User"

    assert client.put("/api/v1/me/favorites/fixture-vision-lab").status_code == 204
    assert "fixture-vision-lab" in client.get("/api/v1/me/favorites").json()["labIds"]

    created = client.post(
        "/api/v1/me/calendar-events",
        json={
            "title": "Contact lab",
            "kind": "contact",
            "date": "2026-08-01",
            "labId": "fixture-vision-lab",
        },
    )
    assert created.status_code == 201
    event_id = created.json()["id"]
    assert [item["id"] for item in client.get("/api/v1/me/calendar-events").json()["items"]] == [
        event_id
    ]
    assert client.delete(f"/api/v1/me/calendar-events/{event_id}").status_code == 204
