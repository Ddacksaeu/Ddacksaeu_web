from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas.email import (
    EmailDraftRequest,
    EmailDraftResponse,
    EmailReviewRequest,
    EmailReviewResponse,
)
from app.services.email_drafting import EmailDraftingError, create_email_draft, review_email

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/draft", response_model=EmailDraftResponse)
def draft_email(
    payload: EmailDraftRequest,
    request: Request,
    user: User = Depends(current_user),  # noqa: B008
    db: Session = Depends(get_db_session),  # noqa: B008
) -> EmailDraftResponse | JSONResponse:
    try:
        return create_email_draft(db, payload, user_id=user.id)
    except EmailDraftingError as error:
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": error.code, "message": error.message}},
            headers={"X-Request-ID": request.state.request_id},
        )


@router.post("/review", response_model=EmailReviewResponse)
def review_email_draft(
    payload: EmailReviewRequest,
    request: Request,
    user: User = Depends(current_user),  # noqa: B008
    db: Session = Depends(get_db_session),  # noqa: B008
) -> EmailReviewResponse | JSONResponse:
    try:
        return review_email(db, payload, user.id)
    except EmailDraftingError as error:
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": error.code, "message": error.message}},
            headers={"X-Request-ID": request.state.request_id},
        )
