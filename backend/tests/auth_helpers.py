from fastapi.testclient import TestClient

from app.core.auth import issue_token


def jwt_headers(client: TestClient, user_id: str = "demo-user") -> dict[str, str]:
    """Build an Authorization header using the application's JWT implementation."""
    token = issue_token(user_id, client.app.state.settings)
    return {"Authorization": f"Bearer {token}"}
