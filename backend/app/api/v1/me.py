from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.db.session import get_db_session
from app.models import User
from app.repositories.me import MeRepository
from app.schemas.me import (
    CalendarEventCreate,
    CalendarEventListResponse,
    CalendarEventResponse,
    CalendarEventUpdate,
    FavoriteListResponse,
    UserProfileResponse,
    UserProfileUpdate,
)

router = APIRouter(prefix="/me", tags=["me"])


def _profile(profile) -> UserProfileResponse:
    return UserProfileResponse(
        name=profile.name,
        affiliation=profile.affiliation,
        status=profile.status,
        program=profile.program,
        interests=profile.interests_json,
        skills=profile.skills_json,
        methodologies=profile.methodologies_json,
        projects=profile.projects_json,
        updated_at=profile.updated_at,
    )


def _event(event) -> CalendarEventResponse:
    return CalendarEventResponse(
        id=event.id,
        title=event.title,
        kind=event.kind,
        date=event.event_date,
        lab_id=event.lab_id,
        memo=event.memo,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.get("/profile", response_model=UserProfileResponse)
def get_profile(
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User, Depends(current_user)],
) -> UserProfileResponse:
    return _profile(MeRepository(session, user.id).profile())


@router.patch("/profile", response_model=UserProfileResponse)
def update_profile(
    payload: UserProfileUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User, Depends(current_user)],
) -> UserProfileResponse:
    profile = MeRepository(session, user.id).profile()
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(
            profile,
            f"{field}_json"
            if field in {"interests", "skills", "methodologies", "projects"}
            else field,
            value,
        )
    session.commit()
    session.refresh(profile)
    return _profile(profile)


@router.get("/favorites", response_model=FavoriteListResponse)
def list_favorites(
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User, Depends(current_user)],
) -> FavoriteListResponse:
    return FavoriteListResponse(lab_ids=MeRepository(session, user.id).favorite_ids())


@router.put("/favorites/{lab_id}", status_code=204)
def add_favorite(
    lab_id: str,
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User, Depends(current_user)],
) -> Response:
    if not MeRepository(session, user.id).add_favorite(lab_id):
        raise HTTPException(status_code=404)
    return Response(status_code=204)


@router.delete("/favorites/{lab_id}", status_code=204)
def delete_favorite(
    lab_id: str,
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User, Depends(current_user)],
) -> Response:
    MeRepository(session, user.id).remove_favorite(lab_id)
    return Response(status_code=204)


@router.get("/calendar-events", response_model=CalendarEventListResponse)
def list_events(
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User, Depends(current_user)],
    from_date: date | None = Query(None, alias="from"),  # noqa: B008
    to: date | None = None,
) -> CalendarEventListResponse:
    if from_date and to and from_date > to:
        raise HTTPException(status_code=422, detail="from must be before to")
    return CalendarEventListResponse(
        items=[_event(event) for event in MeRepository(session, user.id).events(from_date, to)]
    )


@router.post("/calendar-events", response_model=CalendarEventResponse, status_code=201)
def create_event(
    payload: CalendarEventCreate,
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User, Depends(current_user)],
) -> CalendarEventResponse:
    try:
        return _event(MeRepository(session, user.id).create_event(**payload.model_dump()))
    except LookupError as error:
        raise HTTPException(status_code=404) from error


@router.patch("/calendar-events/{event_id}", response_model=CalendarEventResponse)
def update_event(
    event_id: str,
    payload: CalendarEventUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User, Depends(current_user)],
) -> CalendarEventResponse:
    try:
        event = MeRepository(session, user.id).update_event(
            event_id, **payload.model_dump(exclude_unset=True)
        )
    except LookupError as error:
        raise HTTPException(status_code=404) from error
    if event is None:
        raise HTTPException(status_code=404)
    return _event(event)


@router.delete("/calendar-events/{event_id}", status_code=204)
def delete_event(
    event_id: str,
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User, Depends(current_user)],
) -> Response:
    if not MeRepository(session, user.id).delete_event(event_id):
        raise HTTPException(status_code=404)
    return Response(status_code=204)
