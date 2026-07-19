from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecommendationWeights:
    keyword_match: float = 35.0
    cv_lab_similarity: float = 30.0
    research_paper_similarity: float = 20.0
    preference_match: float = 10.0
    data_freshness: float = 5.0

    def validate(self) -> None:
        if round(sum(self.__dict__.values()), 6) != 100.0:
            raise ValueError("Recommendation weights must total 100")


WEIGHTS = RecommendationWeights()
WEIGHTS.validate()
RECENT_PAPER_LIMIT = 5
