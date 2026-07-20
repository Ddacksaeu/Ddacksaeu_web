from fastapi.testclient import TestClient

from scripts.seed import seed_database
from tests.auth_helpers import jwt_headers


def _seed(session_factory) -> None:
    with session_factory() as session:
        seed_database(session)


def test_db_backed_english_local_personalized_draft(client: TestClient, session_factory) -> None:
    _seed(session_factory)

    response = client.post(
        "/api/v1/email/draft",
        json={"labId": "fixture-vision-lab", "userId": "demo-user", "language": "en"},
        headers=jwt_headers(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generationMode"] == "local_rule_based"
    assert "Fixture Vision Lab" in payload["body"]
    assert "Fixture User" in payload["body"]
    assert "Fixture Paper: Not a Real Publication" in payload["body"]
    assert len(payload["body"]) > 700
    assert any("Recent publication:" in note for note in payload["personalizationNotes"])


def test_db_backed_korean_demo_draft(client: TestClient, session_factory) -> None:
    _seed(session_factory)

    response = client.post(
        "/api/v1/email/draft",
        json={"labId": "fixture-vision-lab", "language": "ko"},
        headers=jwt_headers(client),
    )

    assert response.status_code == 200
    assert "교수님께" in response.json()["body"]
    assert "연구 참여 문의드립니다" in response.json()["subject"]


def test_local_email_review_checks_mechanics_flow_and_lab_fit(
    client: TestClient, session_factory
) -> None:
    _seed(session_factory)

    response = client.post(
        "/api/v1/email/review",
        json={
            "labId": "fixture-vision-lab",
            "subject": "Question for professer",
            "body": "Hello, I would would like to join your group.",
            "language": "en",
        },
        headers=jwt_headers(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reviewMode"] == "local_rule_based"
    assert payload["reviewedSubject"] == "Question for professor"
    assert "would would" not in payload["reviewedBody"]
    assert {issue["category"] for issue in payload["issues"]} >= {
        "spelling",
        "flow",
        "professor_fit",
    }


def test_missing_lab_returns_404(client: TestClient, session_factory) -> None:
    _seed(session_factory)

    response = client.post(
        "/api/v1/email/draft", json={"labId": "missing"}, headers=jwt_headers(client)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "lab_not_found"
