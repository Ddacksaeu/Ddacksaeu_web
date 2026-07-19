from fastapi.testclient import TestClient

from scripts.seed import seed_database
from tests.auth_helpers import jwt_headers


def _seed(session_factory) -> None:
    with session_factory() as session:
        seed_database(session)


def test_db_backed_english_demo_draft(client: TestClient, session_factory) -> None:
    _seed(session_factory)

    response = client.post(
        "/api/v1/email/draft",
        json={"labId": "fixture-vision-lab", "userId": "demo-user", "language": "en"},
        headers=jwt_headers(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generationMode"] == "demo"
    assert "Fixture Vision Lab" in payload["body"]
    assert "Fixture User" in payload["body"]


def test_db_backed_korean_demo_draft(client: TestClient, session_factory) -> None:
    _seed(session_factory)

    response = client.post(
        "/api/v1/email/draft",
        json={"labId": "fixture-vision-lab", "language": "ko"},
        headers=jwt_headers(client),
    )

    assert response.status_code == 200
    assert "교수님께" in response.json()["body"]
    assert "연구 관련 문의드립니다" in response.json()["subject"]


def test_missing_lab_returns_404(client: TestClient, session_factory) -> None:
    _seed(session_factory)

    response = client.post(
        "/api/v1/email/draft", json={"labId": "missing"}, headers=jwt_headers(client)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "lab_not_found"
