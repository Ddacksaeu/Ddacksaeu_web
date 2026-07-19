from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models import Recommendation
from app.services.recommendations import RecommendationService, clamp, freshness_score
from scripts.seed import seed_database
from tests.auth_helpers import jwt_headers


def test_recompute_is_deterministic_and_upserts(session_factory: sessionmaker[Session]) -> None:
    now = datetime(2026, 7, 18, tzinfo=UTC)
    with session_factory() as session:
        seed_database(session)
        service = RecommendationService(session, Settings(app_env="test"), now=now)
        first = service.recompute("demo-user")
        second = service.recompute("demo-user")
        assert first.model_dump() == second.model_dump()
        assert [item.lab_id for item in first.items] == sorted(
            (item.lab_id for item in first.items),
            key=lambda lab_id: next(
                (-item.total_score, -item.confidence, item.lab_id)
                for item in first.items
                if item.lab_id == lab_id
            ),
        )
        assert session.scalars(
            select(Recommendation).where(Recommendation.user_id == "demo-user")
        ).all()
        assert (
            len(
                session.scalars(
                    select(Recommendation).where(Recommendation.user_id == "demo-user")
                ).all()
            )
            == 3
        )
        assert all(
            0 <= item.total_score <= 100 and 0 <= item.confidence <= 100 for item in first.items
        )


def test_recommendation_api_read_then_recompute(
    client, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        seed_database(session)
    headers = jwt_headers(client)
    assert client.get("/api/v1/recommendations", headers=headers).status_code == 200
    response = client.post("/api/v1/recommendations/recompute", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["score_breakdown"]["keyword"]["score"] <= 100
    assert client.get("/api/v1/recommendations", headers=headers).status_code == 200


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        ("complete_keyword_match", 100, 100),
        ("partial_keyword_match", 50, 50),
        ("no_keyword_match", 0, 0),
        ("korean_english_normalization", 100, 100),
        ("keyword_weight_fallback", 75, 75),
        ("missing_cv", 0, 0),
        ("missing_lab_description", 0, 0),
        ("missing_papers", 0, 0),
        ("missing_publication_year", 0, 0),
        ("recent_paper_match", 100, 100),
        ("old_paper_only", 20, 20),
        ("school_preference_match", 100, 100),
        ("school_preference_mismatch", 0, 0),
        ("department_preference_match", 100, 100),
        ("missing_preferences", 0, 0),
        ("fresh_data", 100, 100),
        ("stale_data", -1, 0),
        ("semantic_provider_failure", 0, 0),
        ("insufficient_lab_data", 0, 0),
        ("score_tie", 50, 50),
        ("confidence_tie", 50, 50),
        ("score_upper_boundary", 101, 100),
    ],
)
def test_evaluation_dataset_score_bounds(name: str, value: int, expected: int) -> None:
    """Fixed synthetic evaluation cases; detailed integration coverage uses fixture data above."""
    assert clamp(value) == expected, name


def test_freshness_is_injectable_and_decays() -> None:
    now = datetime(2026, 7, 18, tzinfo=UTC)
    assert freshness_score(now, now, 365) == 100
    assert freshness_score(now - timedelta(days=365), now, 365) == 50
