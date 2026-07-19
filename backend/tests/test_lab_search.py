from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from scripts.seed import seed_database
from tests.auth_helpers import jwt_headers


def seed_client_data(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        seed_database(session)


def test_empty_search_returns_all_labs_and_favorite(client: TestClient, session_factory) -> None:
    seed_client_data(session_factory)

    response = client.get("/api/v1/labs", headers=jwt_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["page"] == 1
    assert payload["pageSize"] == 20
    assert any(item["isFavorite"] for item in payload["items"])


def test_korean_keyword_search(client: TestClient, session_factory) -> None:
    seed_client_data(session_factory)

    response = client.get("/api/v1/labs", params={"q": "컴퓨터 비전"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["fixture-vision-lab"]


def test_english_keyword_search(client: TestClient, session_factory) -> None:
    seed_client_data(session_factory)

    response = client.get("/api/v1/labs", params={"q": "multimodal"})

    assert response.status_code == 200
    assert {item["id"] for item in response.json()["items"]} == {
        "fixture-vision-lab",
        "fixture-multimodal-lab",
    }


def test_combined_filters_and_score_sort(client: TestClient, session_factory) -> None:
    seed_client_data(session_factory)

    response = client.get(
        "/api/v1/labs",
        params=[
            ("university", "KAIST"),
            ("department", "AI Graduate"),
            ("field", "Multimodal"),
            ("professor_name", "Min"),
            ("lab_name", "Multimodal"),
            ("sort", "score"),
        ],
        headers=jwt_headers(client),
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["fixture-multimodal-lab"]
    assert response.json()["items"][0]["recommendationScore"] == 84


def test_score_sort_orders_persisted_recommendations_first(
    client: TestClient, session_factory
) -> None:
    seed_client_data(session_factory)

    response = client.get("/api/v1/labs", params={"sort": "score"}, headers=jwt_headers(client))

    assert response.status_code == 200
    assert [item["recommendationScore"] for item in response.json()["items"]] == [87, 84, None]


def test_lab_detail_includes_favorite_and_provenance(client: TestClient, session_factory) -> None:
    seed_client_data(session_factory)

    response = client.get("/api/v1/labs/fixture-vision-lab", headers=jwt_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["isFavorite"] is True
    assert payload["facts"][0]["sourceUrl"] == "https://example.invalid/ddacksaeu-fixtures"
    assert payload["papers"][0]["sourceCheckedAt"] is not None


def test_similar_labs_excludes_current_lab_and_prioritizes_same_field(
    client: TestClient, session_factory
) -> None:
    seed_client_data(session_factory)

    response = client.get("/api/v1/labs/fixture-vision-lab/similar", params={"limit": 3})

    assert response.status_code == 200
    assert "fixture-vision-lab" not in [item["id"] for item in response.json()["items"]]
    assert len(response.json()["items"]) == 2


def test_missing_lab_returns_common_404(client: TestClient, session_factory) -> None:
    seed_client_data(session_factory)

    response = client.get("/api/v1/labs/not-a-lab")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "http_404", "message": "Resource not found"}}


def test_page_boundary_returns_empty_items(client: TestClient, session_factory) -> None:
    seed_client_data(session_factory)

    response = client.get("/api/v1/labs", params={"page": 2, "page_size": 3})

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 3


def test_invalid_sort_returns_validation_error(client: TestClient, session_factory) -> None:
    seed_client_data(session_factory)

    response = client.get("/api/v1/labs", params={"sort": "name"})

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "validation_error", "message": "Request validation failed"}
    }
