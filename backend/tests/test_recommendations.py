from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.config.recommendation_weights import WEIGHTS
from app.repositories.documents import create_completed_analysis, create_uploaded_document
from app.schemas.documents import StructuredDocumentAnalysis
from app.services.recommendation.normalization import normalize_term, normalize_terms
from app.services.recommendations import _freshness, _round
from scripts.seed import seed_database
from tests.auth_helpers import jwt_headers


def test_weights_total_100() -> None:
    assert sum(WEIGHTS.__dict__.values()) == 100


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" PyTorch ", "pytorch"),
        ("ＰｙＴｏｒｃｈ", "pytorch"),
        ("ML", "machine learning"),
        ("computer-vision", "computer vision"),
    ],
)
def test_normalization(value: str, expected: str) -> None:
    assert normalize_term(value) == expected


def test_normalization_is_unique_and_stable() -> None:
    assert normalize_terms([" CV ", "Computer Vision", "CV", "", "ML"]) == [
        "computer vision",
        "machine learning",
    ]


@pytest.mark.parametrize(("days", "expected"), [(0, 100), (31, 80), (91, 60), (181, 40), (366, 20)])
def test_freshness_thresholds(days: int, expected: int) -> None:
    now = datetime(2026, 7, 19, tzinfo=UTC)
    assert _freshness(now - timedelta(days=days), now) == expected


def test_missing_freshness_and_score_clamping() -> None:
    assert _freshness(None, datetime(2026, 7, 19, tzinfo=UTC)) == 0
    assert _round(-1) == 0
    assert _round(100.9) == 100


def test_recommendation_http_requires_cv_then_returns_fixture_results(
    client, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        seed_database(session)
    headers = jwt_headers(client)
    assert client.get("/api/v1/recommendations", headers=headers).status_code == 409
    with session_factory() as session:
        document = create_uploaded_document(
            session,
            user_id="demo-user",
            filename="cv.txt",
            content_type="text/plain",
            byte_size=100,
        )
        create_completed_analysis(
            session,
            document=document,
            result=StructuredDocumentAnalysis(
                skills=["PyTorch"],
                research_interests=["Computer Vision"],
                keywords=["CV"],
                short_summary="CV analysis",
            ),
        )
    response = client.get("/api/v1/recommendations?limit=2", headers=headers)
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["data_origin"] == "fixture"
    assert item["score_breakdown"]["keyword_match"]["max_score"] == 35
