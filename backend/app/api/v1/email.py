from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db_session
from app.schemas.email import EmailDraftRequest, EmailDraftResponse
from app.services.email_drafting import EmailDraftingError, create_email_draft

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/draft", response_model=EmailDraftResponse)
def draft_email(
    payload: EmailDraftRequest,
    request: Request,
    db: Session = Depends(get_db_session),  # noqa: B008
) -> EmailDraftResponse | JSONResponse:
    settings: Settings = request.app.state.settings
    try:
        return create_email_draft(
            db,
            payload,
            api_key=(
                settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
            ),
            model=settings.openai_model,
            timeout_seconds=settings.openai_timeout_seconds,
        )
    except EmailDraftingError as error:
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": error.code, "message": error.message}},
            headers={"X-Request-ID": request.state.request_id},
        )
