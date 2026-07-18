from fastapi.testclient import TestClient


def _signup(client: TestClient, email: str, name: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "secure-password-123", "name": name},
    )
    assert response.status_code == 201
    return response.json()


def _headers(account: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {account['access_token']}"}


def test_signup_login_and_private_data_are_isolated(client: TestClient) -> None:
    first = _signup(client, "first@example.com", "First")
    second = _signup(client, "second@example.com", "Second")
    assert first["user_id"] != second["user_id"]
    assert (
        client.post(
            "/api/v1/auth/signup",
            json={"email": "first@example.com", "password": "secure-password-123", "name": "Again"},
        ).status_code
        == 409
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": "first@example.com", "password": "secure-password-123"}
    )
    assert login.status_code == 200
    assert (
        client.patch(
            "/api/v1/me/profile", headers=_headers(first), json={"name": "Only first"}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/me/profile", headers=_headers(second)).json()["name"] == "Second"
    created = client.post(
        "/api/v1/me/calendar-events",
        headers=_headers(first),
        json={"title": "First event", "kind": "contact", "date": "2026-08-01"},
    )
    assert created.status_code == 201
    assert client.get("/api/v1/me/calendar-events", headers=_headers(second)).json()["items"] == []
    assert client.get("/api/v1/me/profile").status_code == 401
