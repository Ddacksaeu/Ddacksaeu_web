from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.config.recommendation_weights import RECENT_PAPER_LIMIT, WEIGHTS
from app.models import Lab
from app.repositories.recommendations import RecommendationRepository
from app.schemas.recommendations import (
    EvidenceItem,
    RecommendationListResponse,
    RecommendationResponse,
    RecommendationScorePart,
)
from app.services.cv_lab_similarity import compare_cv_to_lab
from app.services.recommendation.normalization import normalize_term, normalize_terms


def _round(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def _freshness(timestamp: datetime | None, now: datetime) -> float:
    if timestamp is None:
        return 0
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    days = max(0, (now - timestamp).days)
    return (
        100
        if days <= 30
        else 80
        if days <= 90
        else 60
        if days <= 180
        else 40
        if days <= 365
        else 20
    )


class RecommendationService:
    def __init__(self, session: Session, now: datetime | None = None) -> None:
        self.repository = RecommendationRepository(session)
        self.now = now or datetime.now(UTC)

    def recommend(
        self,
        user_id: str,
        preferred_university: str | None = None,
        preferred_department: str | None = None,
        minimum_score: float | None = None,
        limit: int = 20,
    ) -> RecommendationListResponse:
        user = self.repository.get_user(user_id)
        if user is None:
            raise LookupError(user_id)
        analysis = self.repository.latest_analysis(user_id)
        if analysis is None:
            raise RuntimeError(
                "A completed CV analysis is required before recommendations can be calculated"
            )
        items = [
            self._calculate(user, analysis, lab, preferred_university, preferred_department)
            for lab in self.repository.labs()
        ]
        if minimum_score is not None:
            items = [item for item in items if item.total_score >= minimum_score]
        items.sort(
            key=lambda item: (
                -item.total_score,
                -item.score_breakdown["keyword_match"].raw_score,
                item.lab_id,
            )
        )
        return RecommendationListResponse(items=items[:limit])

    def _calculate(
        self, user: Any, analysis: Any, lab: Lab, university: str | None, department: str | None
    ) -> RecommendationResponse:
        structured = analysis.structured_analysis_json or {}
        cv_values = (
            list(analysis.skills_json)
            + list(analysis.keywords_json)
            + list(structured.get("research_interests", []))
        )
        cv_values += list(structured.get("keywords", []))
        profile = user.profile
        if profile:
            cv_values += list(profile.skills_json) + list(profile.interests_json)
        cv_terms = normalize_terms(cv_values)
        labels = {normalize_term(value): value.strip() for value in cv_values if value.strip()}
        lab_values = [link.keyword.term_en or link.keyword.term_ko for link in lab.keywords]
        lab_values += [lab.field]
        lab_terms = normalize_terms(lab_values)
        matched = [labels[term] for term in cv_terms if term in set(lab_terms)]
        missing = [labels[term] for term in cv_terms if term not in set(lab_terms)]
        keyword_available = bool(cv_terms and lab_terms)
        keyword_raw = 100 * len(matched) / len(cv_terms) if keyword_available else 0

        cv_text = " ".join([analysis.search_text, *cv_values])
        lab_text = " ".join(filter(None, [lab.summary_text, lab.field, *lab_values]))
        similarity_available = bool(cv_text.strip() and lab_text.strip())
        similarity_raw = (
            compare_cv_to_lab(cv_text, lab_text).similarity_score if similarity_available else 0
        )

        interest_values = list(structured.get("research_interests", [])) + list(
            analysis.keywords_json
        )
        research_text = " ".join(
            interest_values
            + [str(project.get("description", "")) for project in analysis.projects_json]
        )
        papers = sorted(lab.papers, key=lambda paper: (-paper.published_year, paper.id))[
            :RECENT_PAPER_LIMIT
        ]
        paper_text = " ".join(
            " ".join(
                filter(None, [paper.title, paper.abstract, paper.summary, *paper.keywords_json])
            )
            for paper in papers
        )
        paper_available = bool(research_text.strip() and papers)
        paper_raw = (
            compare_cv_to_lab(research_text, paper_text).similarity_score if paper_available else 0
        )

        preference_values: list[bool] = []
        university = university or (profile.affiliation if profile else None)
        department = department or (profile.program if profile else None)
        if university and university.strip():
            preference_values.append(
                normalize_term(university) in normalize_term(lab.professor.university.name)
            )
        if department and department.strip():
            preference_values.append(normalize_term(department) in normalize_term(lab.department))
        preference_available = bool(preference_values)
        preference_raw = (
            100 * sum(preference_values) / len(preference_values) if preference_values else 0
        )
        freshness_at = lab.source_checked_at or lab.updated_at
        freshness_available = freshness_at is not None
        freshness_raw = _freshness(freshness_at, self.now) if freshness_available else 0

        components = (
            ("keyword_match", keyword_raw, WEIGHTS.keyword_match, keyword_available),
            ("cv_lab_similarity", similarity_raw, WEIGHTS.cv_lab_similarity, similarity_available),
            (
                "research_paper_similarity",
                paper_raw,
                WEIGHTS.research_paper_similarity,
                paper_available,
            ),
            ("preference_match", preference_raw, WEIGHTS.preference_match, preference_available),
            ("data_freshness", freshness_raw, WEIGHTS.data_freshness, freshness_available),
        )
        breakdown = {
            name: RecommendationScorePart(
                score=_round(raw * maximum / 100) if available else 0,
                max_score=maximum,
                raw_score=_round(raw),
                available=available,
            )
            for name, raw, maximum, available in components
        }
        warnings = []
        if not paper_available:
            warnings.append(
                "Recent publication data is unavailable or your CV has no research-interest text."
            )
        if not preference_available:
            warnings.append("University and department preferences were not provided.")
        if not freshness_available:
            warnings.append("Lab verification time is unavailable.")
        if not keyword_available:
            warnings.append("Structured CV or lab keyword data is unavailable.")
        evidence = []
        if matched:
            evidence.append(
                EvidenceItem(
                    type="keyword_match",
                    text=f"{', '.join(matched[:3])} appear in both the CV and lab profile.",
                )
            )
        if paper_available and paper_raw > 0:
            evidence.append(
                EvidenceItem(
                    type="research_paper_similarity",
                    text=(
                        "Recent available publications share terms with your CV "
                        "research interests."
                    ),
                )
            )
        if freshness_available:
            evidence.append(
                EvidenceItem(
                    type="data_freshness",
                    text=f"Lab data was last checked {freshness_at.date().isoformat()}.",
                )
            )
        if len(matched) >= 3:
            reason = f"Strong match in {', '.join(matched[:3])}."
        elif paper_available and paper_raw >= 30:
            reason = "The lab's recent publications align with your research interests."
        elif warnings:
            reason = (
                "This recommendation has limited evidence because some profile data is unavailable."
            )
        else:
            reason = "This recommendation is based on the available CV and lab information."
        completeness = sum(available for _, _, _, available in components) / len(components)
        return RecommendationResponse(
            lab_id=lab.id,
            lab_name=lab.name,
            professor_name=lab.professor_name,
            university=lab.professor.university.name,
            department=lab.department,
            total_score=_round(sum(item.score for item in breakdown.values())),
            matched_keywords=matched,
            missing_keywords=missing,
            score_breakdown=breakdown,
            evidence=evidence,
            short_reason=reason,
            recommended_action="Review the lab's recent publications and save this professor.",
            data_completeness=round(completeness, 2),
            warnings=warnings,
            data_origin=lab.summary_origin,
            calculated_at=self.now,
        )
