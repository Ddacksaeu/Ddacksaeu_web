from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas.recommendations import RecommendationListResponse
from app.services.recommendations import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _service(request: Request, db: Session) -> RecommendationService:
    return RecommendationService(db, request.app.state.settings)


@router.get("", response_model=RecommendationListResponse)
def list_recommendations(
    request: Request,
    user: User = Depends(current_user),  # noqa: B008
    db: Session = Depends(get_db_session),  # noqa: B008
) -> RecommendationListResponse:
    try:
        return _service(request, db).list_persisted(user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="User not found") from error


@router.post("/recompute", response_model=RecommendationListResponse)
def recompute_recommendations(
    request: Request,
    user: User = Depends(current_user),  # noqa: B008
    db: Session = Depends(get_db_session),  # noqa: B008
) -> RecommendationListResponse:
    try:
        return _service(request, db).recompute(user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="User not found") from error
