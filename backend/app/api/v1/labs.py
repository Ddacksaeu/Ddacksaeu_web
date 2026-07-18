from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import optional_current_user
from app.db.session import get_db_session
from app.models import User
from app.repositories.labs import LabSearchFilters
from app.schemas.labs import LabDetail, LabSearchResponse, SimilarLabsResponse
from app.services.lab_search import LabSearchService

router = APIRouter(prefix="/labs", tags=["labs"])

LAB_SEARCH_EXAMPLE = {
    "items": [
        {
            "id": "fixture-vision-lab",
            "name": "Fixture Vision Lab",
            "professorName": "Fixture Han",
            "university": "Fixture Seoul National University",
            "department": "Fixture Computer Science",
            "field": "Computer Vision",
            "summary": "Fictional fixture data for local development only.",
            "keywords": ["컴퓨터 비전", "멀티모달"],
            "homepageUrl": None,
            "updatedAt": "2026-07-18T00:00:00Z",
            "recommendationScore": 87,
            "isFavorite": True,
        }
    ],
    "page": 1,
    "pageSize": 20,
    "total": 1,
}


@router.get(
    "",
    response_model=LabSearchResponse,
    responses={200: {"content": {"application/json": {"example": LAB_SEARCH_EXAMPLE}}}},
)
def search_labs(
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User | None, Depends(optional_current_user)],
    university: Annotated[str | None, Query(min_length=1)] = None,
    department: Annotated[str | None, Query(min_length=1)] = None,
    field: Annotated[list[str] | None, Query(min_length=1)] = None,
    q: Annotated[str | None, Query(min_length=1)] = None,
    professor_name: Annotated[str | None, Query(min_length=1)] = None,
    lab_name: Annotated[str | None, Query(min_length=1)] = None,
    sort: Literal["score", "recent"] = "recent",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> LabSearchResponse:
    filters = LabSearchFilters(
        university=university,
        department=department,
        fields=tuple(field or []),
        query=q,
        professor_name=professor_name,
        lab_name=lab_name,
        sort=sort,
    )
    return LabSearchService(session, user.id if user else None).search(filters, page, page_size)


@router.get("/{lab_id}", response_model=LabDetail)
def get_lab(
    lab_id: str,
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User | None, Depends(optional_current_user)],
) -> LabDetail:
    lab = LabSearchService(session, user.id if user else None).get_detail(lab_id)
    if lab is None:
        raise HTTPException(status_code=404)
    return lab


@router.get("/{lab_id}/similar", response_model=SimilarLabsResponse)
def get_similar_labs(
    lab_id: str,
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User | None, Depends(optional_current_user)],
    limit: Annotated[int, Query(ge=1, le=12)] = 3,
) -> SimilarLabsResponse:
    similar = LabSearchService(session, user.id if user else None).get_similar(lab_id, limit)
    if similar is None:
        raise HTTPException(status_code=404)
    return similar
