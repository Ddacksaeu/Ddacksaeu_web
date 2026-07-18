from fastapi.testclient import TestClient

from app.schemas.health import HealthResponse


def test_health_returns_200_and_expected_schema(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = HealthResponse.model_validate(response.json())
    assert payload.status == "ok"
    assert payload.service == "ddacksaeu-backend"
    assert payload.version == "0.1.0"


def test_unknown_endpoint_uses_common_error_response(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "http_404", "message": "Resource not found"}}


def test_request_id_is_returned(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "test-request-id"})

    assert response.headers["X-Request-ID"] == "test-request-id"
