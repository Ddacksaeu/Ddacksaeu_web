from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import current_user, hash_password, issue_token, verify_password
from app.db.session import get_db_session
from app.models import User, UserProfile
from app.schemas.auth import AuthResponse, LoginRequest, SignupRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def _response(user: User, request: Request) -> AuthResponse:
    return AuthResponse(
        access_token=issue_token(user.id, request.app.state.settings),
        user_id=user.id,
        email=user.email,
        name=user.profile.name if user.profile else "",
    )


@router.post("/signup", response_model=AuthResponse, status_code=201)
def signup(
    payload: SignupRequest,
    request: Request,
    session: Session = Depends(get_db_session),  # noqa: B008
) -> AuthResponse:
    email = payload.email.lower()
    if session.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(id=str(uuid4()), email=email, password_hash=hash_password(payload.password))
    user.profile = UserProfile(user_id=user.id, name=payload.name)
    session.add(user)
    session.commit()
    session.refresh(user)
    return _response(user, request)


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    session: Session = Depends(get_db_session),  # noqa: B008
) -> AuthResponse:
    user = session.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _response(user, request)


@router.get("/me", response_model=AuthResponse)
def me(request: Request, user: User = Depends(current_user)) -> AuthResponse:  # noqa: B008
    return _response(user, request)
