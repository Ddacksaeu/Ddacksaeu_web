from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Favorite, Keyword, Lab, LabKeyword, Professor, Recommendation, University

DEMO_USER_ID = "demo-user"


@dataclass(frozen=True)
class LabSearchFilters:
    university: str | None = None
    department: str | None = None
    fields: tuple[str, ...] = ()
    query: str | None = None
    professor_name: str | None = None
    lab_name: str | None = None
    sort: str = "recent"


class LabRepository:
    def __init__(self, session: Session, user_id: str = DEMO_USER_ID) -> None:
        self.session = session
        self.user_id = user_id

    def search(self, filters: LabSearchFilters, page: int, page_size: int) -> tuple[list, int]:
        statement = self._base_statement(filters)
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        statement = self._apply_sort(statement, filters.sort)
        rows = self.session.execute(statement.offset((page - 1) * page_size).limit(page_size)).all()
        return rows, total

    def get_by_id(self, lab_id: str):
        favorite_exists = select(Favorite.lab_id).where(
            Favorite.user_id == self.user_id, Favorite.lab_id == Lab.id
        )
        recommendation_score = (
            select(Recommendation.total_score)
            .where(Recommendation.user_id == self.user_id, Recommendation.lab_id == Lab.id)
            .scalar_subquery()
        )
        statement = (
            select(
                Lab,
                University.name.label("university"),
                recommendation_score.label("recommendation_score"),
                favorite_exists.exists().label("is_favorite"),
            )
            .join(Lab.professor)
            .join(Professor.university)
            .where(Lab.id == lab_id)
            .options(
                selectinload(Lab.keywords).selectinload(LabKeyword.keyword),
                selectinload(Lab.facts),
                selectinload(Lab.papers),
            )
        )
        return self.session.execute(statement).one_or_none()

    def _base_statement(self, filters: LabSearchFilters) -> Select:
        favorite_exists = select(Favorite.lab_id).where(
            Favorite.user_id == self.user_id, Favorite.lab_id == Lab.id
        )
        recommendation_score = (
            select(Recommendation.total_score)
            .where(Recommendation.user_id == self.user_id, Recommendation.lab_id == Lab.id)
            .scalar_subquery()
        )
        statement = (
            select(
                Lab,
                University.name.label("university"),
                recommendation_score.label("recommendation_score"),
                favorite_exists.exists().label("is_favorite"),
            )
            .join(Lab.professor)
            .join(Professor.university)
            .options(selectinload(Lab.keywords).selectinload(LabKeyword.keyword))
        )
        if filters.university:
            statement = statement.where(University.name.ilike(self._pattern(filters.university)))
        if filters.department:
            statement = statement.where(Lab.department.ilike(self._pattern(filters.department)))
        if filters.fields:
            statement = statement.where(
                or_(*(Lab.field.ilike(self._pattern(item)) for item in filters.fields))
            )
        if filters.professor_name:
            statement = statement.where(
                Lab.professor_name.ilike(self._pattern(filters.professor_name))
            )
        if filters.lab_name:
            statement = statement.where(Lab.name.ilike(self._pattern(filters.lab_name)))
        if filters.query:
            pattern = self._pattern(filters.query)
            keyword_match = Lab.keywords.any(
                LabKeyword.keyword.has(
                    or_(Keyword.term_ko.ilike(pattern), Keyword.term_en.ilike(pattern))
                )
            )
            statement = statement.where(
                or_(
                    Lab.name.ilike(pattern),
                    Lab.professor_name.ilike(pattern),
                    Lab.field.ilike(pattern),
                    Lab.summary_text.ilike(pattern),
                    keyword_match,
                )
            )
        return statement

    @staticmethod
    def _apply_sort(statement: Select, sort: str) -> Select:
        if sort == "score":
            return statement.order_by(
                desc("recommendation_score").nulls_last(), Lab.updated_at.desc(), Lab.name.asc()
            )
        return statement.order_by(Lab.updated_at.desc(), Lab.name.asc())

    @staticmethod
    def _pattern(value: str) -> str:
        return f"%{value.strip()}%"
