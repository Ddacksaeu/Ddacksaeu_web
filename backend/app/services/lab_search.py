from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.labs import LabRepository, LabSearchFilters
from app.schemas.labs import (
    LabDetail,
    LabFactResponse,
    LabListItem,
    LabSearchResponse,
    PaperResponse,
    SimilarLabsResponse,
)


class LabSearchService:
    def __init__(self, session: Session) -> None:
        self.repository = LabRepository(session)

    def search(self, filters: LabSearchFilters, page: int, page_size: int) -> LabSearchResponse:
        rows, total = self.repository.search(filters, page, page_size)
        return LabSearchResponse(
            items=[self._list_item(*row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_detail(self, lab_id: str) -> LabDetail | None:
        row = self.repository.get_by_id(lab_id)
        if row is None:
            return None
        lab, university, recommendation_score, is_favorite = row
        item = self._list_item(lab, university, recommendation_score, is_favorite)
        return LabDetail(
            **item.model_dump(),
            location=lab.location,
            contact_email=lab.contact_email,
            source_url=lab.source_url,
            source_checked_at=lab.source_checked_at,
            facts=[LabFactResponse.model_validate(fact) for fact in lab.facts],
            papers=[
                PaperResponse(
                    id=paper.id,
                    title=paper.title,
                    venue=paper.venue,
                    published_year=paper.published_year,
                    abstract=paper.abstract,
                    summary=paper.summary,
                    keywords=paper.keywords_json,
                    paper_url=paper.paper_url,
                    source_url=paper.source_url,
                    source_checked_at=paper.source_checked_at,
                )
                for paper in lab.papers
            ],
        )

    def get_similar(self, lab_id: str, limit: int) -> SimilarLabsResponse | None:
        if self.repository.get_by_id(lab_id) is None:
            return None
        return SimilarLabsResponse(
            items=[self._list_item(*row) for row in self.repository.list_similar(lab_id, limit)]
        )

    @staticmethod
    def _list_item(
        lab, university: str, recommendation_score: int | None, is_favorite: bool
    ) -> LabListItem:
        return LabListItem(
            id=lab.id,
            name=lab.name,
            professor_name=lab.professor_name,
            university=university,
            department=lab.department,
            field=lab.field,
            summary=lab.summary_text,
            keywords=[link.keyword.term_ko for link in lab.keywords],
            homepage_url=lab.homepage_url,
            updated_at=lab.updated_at,
            recommendation_score=recommendation_score,
            is_favorite=is_favorite,
        )
