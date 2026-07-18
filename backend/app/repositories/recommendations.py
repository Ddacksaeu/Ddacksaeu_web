from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    DocumentAnalysis,
    Lab,
    LabKeyword,
    Professor,
    Recommendation,
    UploadedDocument,
    User,
    UserKeyword,
)


class RecommendationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_user(self, user_id: str) -> User | None:
        return self.session.scalar(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.profile),
                selectinload(User.keywords).selectinload(UserKeyword.keyword),
            )
        )

    def labs(self) -> list[Lab]:
        return list(
            self.session.scalars(
                select(Lab).options(
                    selectinload(Lab.professor).selectinload(Professor.university),
                    selectinload(Lab.keywords).selectinload(LabKeyword.keyword),
                    selectinload(Lab.papers),
                )
            )
        )

    def latest_analysis(self, user_id: str) -> DocumentAnalysis | None:
        statement = (
            select(DocumentAnalysis)
            .join(UploadedDocument)
            .where(UploadedDocument.user_id == user_id, DocumentAnalysis.status == "completed")
            .order_by(DocumentAnalysis.created_at.desc(), DocumentAnalysis.id.asc())
        )
        return self.session.scalar(statement)

    def upsert(self, recommendation: Recommendation) -> Recommendation:
        existing = self.session.scalar(
            select(Recommendation).where(
                Recommendation.user_id == recommendation.user_id,
                Recommendation.lab_id == recommendation.lab_id,
            )
        )
        if existing is None:
            self.session.add(recommendation)
            return recommendation
        for field in (
            "keyword_score",
            "semantic_score",
            "research_score",
            "preference_score",
            "total_score",
            "confidence",
            "reason",
            "score_breakdown",
        ):
            setattr(existing, field, getattr(recommendation, field))
        return existing

    def persisted(self, user_id: str) -> list[Recommendation]:
        return list(
            self.session.scalars(
                select(Recommendation)
                .where(Recommendation.user_id == user_id)
                .options(
                    selectinload(Recommendation.lab)
                    .selectinload(Lab.professor)
                    .selectinload(Professor.university)
                )
            )
        )
