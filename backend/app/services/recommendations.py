from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Lab, Recommendation
from app.repositories.recommendations import RecommendationRepository
from app.schemas.recommendations import (
    RecommendationListResponse,
    RecommendationResponse,
    RecommendationScorePart,
)
from app.services.recommendation_similarity import (
    DeterministicLexicalSimilarityProvider,
    OpenAIEmbeddingSimilarityProvider,
    SemanticSimilarityProvider,
    tokens,
)

WEIGHTS = {
    "keyword": 0.35,
    "semantic": 0.30,
    "research": 0.20,
    "preference": 0.10,
    "freshness": 0.05,
}
if round(sum(WEIGHTS.values()), 8) != 1:
    raise RuntimeError("Recommendation weights must total 1.0")


def clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def freshness_score(timestamp: datetime | None, now: datetime, half_life_days: int) -> int:
    """A verified/crawled record loses half its freshness every configured interval."""
    if timestamp is None:
        return 0
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    days = max(0.0, (now - timestamp.astimezone(UTC)).total_seconds() / 86_400)
    return clamp(100 * (0.5 ** (days / max(1, half_life_days))))


@dataclass(frozen=True)
class CalculatedRecommendation:
    response: RecommendationResponse
    record: Recommendation


class RecommendationService:
    def __init__(self, session: Session, settings: Settings, now: datetime | None = None) -> None:
        self.repository = RecommendationRepository(session)
        self.settings = settings
        self.now = now or datetime.now(UTC)

    def recompute(self, user_id: str) -> RecommendationListResponse:
        user = self.repository.get_user(user_id)
        if user is None:
            raise LookupError(user_id)
        analysis = self.repository.latest_analysis(user_id)
        results = [self._calculate(user, analysis, lab) for lab in self.repository.labs()]
        for result in results:
            self.repository.upsert(result.record)
        self.repository.session.commit()
        return RecommendationListResponse(
            items=self._sorted([result.response for result in results])
        )

    def list_persisted(self, user_id: str) -> RecommendationListResponse:
        if self.repository.get_user(user_id) is None:
            raise LookupError(user_id)
        items = [self._from_record(record) for record in self.repository.persisted(user_id)]
        return RecommendationListResponse(items=self._sorted(items))

    @staticmethod
    def _sorted(items: list[RecommendationResponse]) -> list[RecommendationResponse]:
        return sorted(items, key=lambda item: (-item.total_score, -item.confidence, item.lab_id))

    def _provider(self) -> tuple[SemanticSimilarityProvider, bool]:
        if self.settings.recommendation_semantic_provider != "openai":
            return DeterministicLexicalSimilarityProvider(), False
        if not self.settings.openai_api_key:
            return DeterministicLexicalSimilarityProvider(), True
        try:
            return (
                OpenAIEmbeddingSimilarityProvider(
                    self.settings.openai_api_key.get_secret_value(),
                    self.settings.recommendation_embedding_model,
                ),
                False,
            )
        except Exception:  # provider construction must not fail a recommendation request
            return DeterministicLexicalSimilarityProvider(), True

    def _calculate(self, user: Any, analysis: Any, lab: Lab) -> CalculatedRecommendation:
        profile = user.profile
        user_terms = [(link.keyword.term_ko, link.keyword.term_en) for link in user.keywords]
        keyword_weights = {ko: 1.0 for ko, _ in user_terms}
        lab_terms = {
            term
            for link in lab.keywords
            for term in (link.keyword.term_ko, link.keyword.term_en)
            if term
        }
        normalized_lab = {term.lower() for term in lab_terms}
        matched = sorted(
            ko
            for ko, en in user_terms
            if ko.lower() in normalized_lab or (en and en.lower() in normalized_lab)
        )
        missing = sorted(ko for ko, _ in user_terms if ko not in matched)
        keyword_available = bool(user_terms and lab_terms)
        keyword_score = clamp(100 * len(matched) / len(user_terms)) if keyword_available else 0

        user_text_parts = []
        if profile:
            user_text_parts.extend(
                profile.interests_json
                + profile.skills_json
                + profile.methodologies_json
                + profile.projects_json
            )
        if analysis:
            user_text_parts.extend(
                analysis.keywords_json + analysis.skills_json + analysis.methodologies_json
            )
            user_text_parts.extend(
                project.get("description", "") for project in analysis.projects_json
            )
        user_text = " ".join(user_text_parts)
        lab_text = " ".join(filter(None, [lab.summary_text, lab.field, *lab_terms]))
        semantic_available = bool(user_text.strip() and lab_text.strip())
        provider, provider_degraded = self._provider()
        semantic_degraded = provider_degraded
        try:
            semantic_score = (
                clamp(provider.similarity(user_text, lab_text) * 100) if semantic_available else 0
            )
        except Exception:
            semantic_score = clamp(
                DeterministicLexicalSimilarityProvider().similarity(user_text, lab_text) * 100
            )
            semantic_degraded = True

        interests = profile.interests_json if profile else []
        research_terms = tokens(" ".join(interests))
        papers = sorted(
            lab.papers, key=lambda paper: (paper.published_year, paper.id), reverse=True
        )[:3]
        paper_scores = []
        for paper in papers:
            paper_text = " ".join(
                filter(None, [paper.title, paper.abstract, paper.summary, *paper.keywords_json])
            )
            paper_scores.append(
                100 * len(research_terms & tokens(paper_text)) / len(research_terms)
                if research_terms
                else 0
            )
        research_available = bool(research_terms and papers)
        research_score = clamp(sum(paper_scores) / len(paper_scores)) if research_available else 0

        preference_values = []
        if profile and profile.affiliation.strip():
            preference_values.append(
                100.0
                if profile.affiliation.lower() in lab.professor.university.name.lower()
                else 0.0
            )
        if profile and profile.program.strip():
            preference_values.append(
                100.0 if profile.program.lower() in lab.department.lower() else 0.0
            )
        preference_available = bool(preference_values)
        preference_score = (
            clamp(sum(preference_values) / len(preference_values)) if preference_available else 0
        )

        fresh_at = lab.source_checked_at or lab.updated_at
        freshness_available = fresh_at is not None
        fresh_score = (
            freshness_score(
                fresh_at, self.now, self.settings.recommendation_freshness_half_life_days
            )
            if freshness_available
            else 0
        )
        scores = {
            "keyword": (keyword_score, keyword_available, False),
            "semantic": (semantic_score, semantic_available, semantic_degraded),
            "research": (research_score, research_available, False),
            "preference": (preference_score, preference_available, False),
            "freshness": (fresh_score, freshness_available, False),
        }
        usable_weight = sum(
            WEIGHTS[name] for name, (_, available, _) in scores.items() if available
        )
        breakdown: dict[str, RecommendationScorePart] = {}
        for name, (score, available, degraded) in scores.items():
            effective_weight = WEIGHTS[name] / usable_weight if available and usable_weight else 0
            breakdown[name] = RecommendationScorePart(
                score=score,
                weight=effective_weight,
                contribution=round(score * effective_weight, 2),
                unavailable=not available,
                degraded=degraded,
            )
        total = clamp(sum(part.contribution for part in breakdown.values())) if usable_weight else 0
        user_complete = sum(bool(value) for value in (user_terms, user_text.strip(), interests)) / 3
        lab_complete = (
            sum(bool(value) for value in (lab_terms, lab_text.strip(), papers, fresh_at)) / 4
        )
        confidence = clamp(
            100
            * (0.55 * usable_weight + 0.25 * user_complete + 0.20 * lab_complete)
            * (0.8 if semantic_degraded else 1)
        )
        evidence = {
            "matched_keywords": matched,
            "paper_ids": [paper.id for paper in papers],
            "source_checked_at": fresh_at.isoformat() if fresh_at else None,
            "semantic_provider": "deterministic_lexical"
            if semantic_degraded
            or self.settings.recommendation_semantic_provider == "deterministic"
            else "openai_embedding",
        }
        short_reason, action = self._explanation(
            matched, missing, research_available, semantic_degraded
        )
        response = RecommendationResponse(
            lab_id=lab.id,
            lab_name=lab.name,
            professor_name=lab.professor_name,
            university=lab.professor.university.name,
            department=lab.department,
            total_score=total,
            confidence=confidence,
            matched_keywords=matched,
            missing_keywords=missing,
            user_keyword_weights=keyword_weights,
            score_breakdown=breakdown,
            evidence=evidence,
            short_reason=short_reason,
            recommended_action=action,
            calculated_at=self.now,
        )
        record = Recommendation(
            user_id=user.id,
            lab_id=lab.id,
            keyword_score=keyword_score,
            semantic_score=semantic_score,
            research_score=research_score,
            preference_score=preference_score,
            total_score=total,
            confidence=confidence,
            reason=short_reason,
            score_breakdown={
                "components": {key: value.model_dump() for key, value in breakdown.items()},
                "evidence": evidence,
                "matched_keywords": matched,
                "missing_keywords": missing,
                "user_keyword_weights": keyword_weights,
                "recommended_action": action,
                "calculated_at": self.now.isoformat(),
            },
        )
        return CalculatedRecommendation(response=response, record=record)

    @staticmethod
    def _explanation(
        matched: list[str], missing: list[str], has_papers: bool, degraded: bool
    ) -> tuple[str, str]:
        reason = (
            f"Matched keywords: {', '.join(matched)}."
            if matched
            else "No structured keyword overlap was found."
        )
        if has_papers:
            reason += " Recent available papers were included."
        if degraded:
            reason += " Semantic similarity used the deterministic fallback."
        action = (
            "Review the lab description and source-linked papers before contacting the professor."
        )
        if missing:
            action = (
                "Review missing interests and verify fit against the lab's "
                "source-linked information."
            )
        return reason, action

    def _from_record(self, record: Recommendation) -> RecommendationResponse:
        stored = record.score_breakdown or {}
        components = stored.get("components", {})
        if not components:
            components = {
                "keyword": {
                    "score": record.keyword_score,
                    "weight": WEIGHTS["keyword"],
                    "contribution": record.keyword_score * WEIGHTS["keyword"],
                },
                "semantic": {
                    "score": record.semantic_score,
                    "weight": WEIGHTS["semantic"],
                    "contribution": record.semantic_score * WEIGHTS["semantic"],
                },
                "research": {
                    "score": record.research_score,
                    "weight": WEIGHTS["research"],
                    "contribution": record.research_score * WEIGHTS["research"],
                },
                "preference": {
                    "score": record.preference_score,
                    "weight": WEIGHTS["preference"],
                    "contribution": record.preference_score * WEIGHTS["preference"],
                },
                "freshness": {"score": 0, "weight": 0, "contribution": 0, "unavailable": True},
            }
        return RecommendationResponse(
            lab_id=record.lab_id,
            lab_name=record.lab.name,
            professor_name=record.lab.professor_name,
            university=record.lab.professor.university.name,
            department=record.lab.department,
            total_score=record.total_score,
            confidence=record.confidence,
            matched_keywords=stored.get("matched_keywords", []),
            missing_keywords=stored.get("missing_keywords", []),
            user_keyword_weights=stored.get("user_keyword_weights", {}),
            score_breakdown={
                key: RecommendationScorePart.model_validate(value)
                for key, value in components.items()
            },
            evidence=stored.get("evidence", {}),
            short_reason=record.reason,
            recommended_action=stored.get(
                "recommended_action", "Review the available source information before deciding."
            ),
            calculated_at=record.updated_at,
        )
