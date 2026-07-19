from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas.recommendations import RecommendationListResponse
from app.services.recommendations import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationListResponse)
def list_recommendations(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    preferred_university: str | None = None,
    preferred_department: str | None = None,
    minimum_score: float | None = Query(None, ge=0, le=100),
    user: User = Depends(current_user),  # noqa: B008
    db: Session = Depends(get_db_session),  # noqa: B008
) -> RecommendationListResponse:
    try:
        return RecommendationService(db).recommend(
            user.id, preferred_university, preferred_department, minimum_score, limit
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail="User not found") from error
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
