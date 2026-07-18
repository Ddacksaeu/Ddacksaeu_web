from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db_session
from app.models import User

_bearer = HTTPBearer(auto_error=False)
_iterations = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _iterations)
    return f"pbkdf2_sha256${_iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, iterations, salt, digest = encoded.split("$")
        candidate = hashlib.pbkdf2_hmac(
            algorithm.removeprefix("pbkdf2_"),
            password.encode(),
            bytes.fromhex(salt),
            int(iterations),
        )
        return hmac.compare_digest(candidate.hex(), digest)
    except (TypeError, ValueError):
        return False


def _segment(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def issue_token(user_id: str, settings: Settings) -> str:
    now = datetime.now(UTC)
    header = _segment(b'{"alg":"HS256","typ":"JWT"}')
    payload = _segment(
        json.dumps(
            {
                "sub": user_id,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(seconds=settings.auth_token_ttl_seconds)).timestamp()),
            },
            separators=(",", ":"),
        ).encode()
    )
    signature = _segment(
        hmac.new(
            settings.auth_secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256
        ).digest()
    )
    return f"{header}.{payload}.{signature}"


def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),  # noqa: B008
    session: Session = Depends(get_db_session),  # noqa: B008
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        settings: Settings = request.app.state.settings
        header, payload, signature = credentials.credentials.split(".")
        expected = _segment(
            hmac.new(
                settings.auth_secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256
            ).digest()
        )
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if (
            not hmac.compare_digest(signature, expected)
            or int(data["exp"]) < datetime.now(UTC).timestamp()
        ):
            raise ValueError
        user = session.get(User, data["sub"])
    except (ValueError, KeyError, json.JSONDecodeError):
        user = None
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),  # noqa: B008
    session: Session = Depends(get_db_session),  # noqa: B008
) -> User | None:
    if credentials is None:
        return None
    return current_user(request, credentials, session)
