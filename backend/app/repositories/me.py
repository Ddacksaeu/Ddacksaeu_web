from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CalendarEvent, Favorite, Lab, User, UserProfile


class MeRepository:
    def __init__(self, session: Session, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    def profile(self) -> UserProfile:
        profile = self.session.get(UserProfile, self.user_id)
        if profile is not None:
            return profile
        user = self.session.get(User, self.user_id)
        if user is None:
            user = User(id=self.user_id)
            self.session.add(user)
        profile = UserProfile(user_id=self.user_id)
        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)
        return profile

    def favorite_ids(self) -> list[str]:
        return list(
            self.session.scalars(
                select(Favorite.lab_id)
                .where(Favorite.user_id == self.user_id)
                .order_by(Favorite.created_at)
            )
        )

    def add_favorite(self, lab_id: str) -> bool:
        if self.session.get(Lab, lab_id) is None:
            return False
        if self.session.get(Favorite, {"user_id": self.user_id, "lab_id": lab_id}) is None:
            self.session.add(Favorite(user_id=self.user_id, lab_id=lab_id))
            self.session.commit()
        return True

    def remove_favorite(self, lab_id: str) -> None:
        favorite = self.session.get(Favorite, {"user_id": self.user_id, "lab_id": lab_id})
        if favorite is not None:
            self.session.delete(favorite)
            self.session.commit()

    def events(self, start: date | None, end: date | None) -> list[CalendarEvent]:
        statement = select(CalendarEvent).where(CalendarEvent.user_id == self.user_id)
        if start:
            statement = statement.where(CalendarEvent.event_date >= start)
        if end:
            statement = statement.where(CalendarEvent.event_date <= end)
        return list(
            self.session.scalars(
                statement.order_by(CalendarEvent.event_date, CalendarEvent.created_at)
            )
        )

    def create_event(self, **values) -> CalendarEvent:
        if values.get("lab_id") and self.session.get(Lab, values["lab_id"]) is None:
            raise LookupError(values["lab_id"])
        event = CalendarEvent(user_id=self.user_id, event_date=values.pop("date"), **values)
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def delete_event(self, event_id: str) -> bool:
        event = self.session.get(CalendarEvent, event_id)
        if event is None or event.user_id != self.user_id:
            return False
        self.session.delete(event)
        self.session.commit()
        return True

    def update_event(self, event_id: str, **values) -> CalendarEvent | None:
        event = self.session.get(CalendarEvent, event_id)
        if event is None or event.user_id != self.user_id:
            return None
        if values.get("lab_id") and self.session.get(Lab, values["lab_id"]) is None:
            raise LookupError(values["lab_id"])
        for field, value in values.items():
            setattr(event, "event_date" if field == "date" else field, value)
        self.session.commit()
        self.session.refresh(event)
        return event
