from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.recommendations import RecommendationListResponse
from app.services.recommendations import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _service(request: Request, db: Session) -> RecommendationService:
    return RecommendationService(db, request.app.state.settings)


@router.get("", response_model=RecommendationListResponse)
def list_recommendations(
    request: Request,
    user_id: str = Query("demo-user"),
    db: Session = Depends(get_db_session),  # noqa: B008
) -> RecommendationListResponse:
    try:
        return _service(request, db).list_persisted(user_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="User not found") from error


@router.post("/recompute", response_model=RecommendationListResponse)
def recompute_recommendations(
    request: Request,
    user_id: str = Query("demo-user"),
    db: Session = Depends(get_db_session),  # noqa: B008
) -> RecommendationListResponse:
    try:
        return _service(request, db).recompute(user_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="User not found") from error
