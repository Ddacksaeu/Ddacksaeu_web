from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, TypeVar

from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.models import (
    AdmissionEvent,
    CrawlRun,
    CrawlSource,
    Department,
    Favorite,
    Keyword,
    Lab,
    LabFact,
    LabKeyword,
    Paper,
    Professor,
    Recommendation,
    University,
    User,
    UserKeyword,
    UserProfile,
)

FIXTURE_SOURCE_URL = "https://example.invalid/ddacksaeu-fixtures"
FIXTURE_CHECKED_AT = datetime(2026, 7, 18, tzinfo=UTC)
ModelType = TypeVar("ModelType")


def add_if_missing(
    session: Session, model: type[ModelType], identifier: Any, **values: Any
) -> None:
    if session.get(model, identifier) is None:
        session.add(model(**values))


def seed_database(session: Session) -> None:
    """Insert idempotent, explicitly fictional data for local development only."""
    for university_id, name in (
        ("fixture-seoul-national", "Fixture Seoul National University"),
        ("fixture-kaist", "Fixture KAIST"),
        ("fixture-postech", "Fixture POSTECH"),
    ):
        add_if_missing(
            session,
            University,
            university_id,
            id=university_id,
            name=name,
            country="KR",
            source_url=FIXTURE_SOURCE_URL,
            source_checked_at=FIXTURE_CHECKED_AT,
        )

    departments = (
        ("fixture-snu-cse", "fixture-seoul-national", "Fixture Computer Science"),
        ("fixture-kaist-ai", "fixture-kaist", "Fixture AI Graduate School"),
        ("fixture-postech-cse", "fixture-postech", "Fixture Computer Science"),
    )
    for department_id, university_id, name in departments:
        add_if_missing(
            session,
            Department,
            department_id,
            id=department_id,
            university_id=university_id,
            name=name,
        )

    professors = (
        ("fixture-snu-professor", "fixture-seoul-national", "fixture-snu-cse", "Fixture Han"),
        ("fixture-kaist-professor", "fixture-kaist", "fixture-kaist-ai", "Fixture Min"),
        ("fixture-postech-professor", "fixture-postech", "fixture-postech-cse", "Fixture Park"),
    )
    for professor_id, university_id, department_id, name in professors:
        add_if_missing(
            session,
            Professor,
            professor_id,
            id=professor_id,
            university_id=university_id,
            department_id=department_id,
            name=name,
            source_url=FIXTURE_SOURCE_URL,
            source_checked_at=FIXTURE_CHECKED_AT,
        )

    keywords = (
        ("fixture-computer-vision", "컴퓨터 비전", "Computer Vision"),
        ("fixture-multimodal", "멀티모달", "Multimodal"),
        ("fixture-robotics", "로보틱스", "Robotics"),
        ("fixture-ml-systems", "머신러닝 시스템", "Machine Learning Systems"),
    )
    for keyword_id, term_ko, term_en in keywords:
        add_if_missing(
            session,
            Keyword,
            keyword_id,
            id=keyword_id,
            term_ko=term_ko,
            term_en=term_en,
            normalized_term=term_en.lower(),
        )

    labs = (
        (
            "fixture-vision-lab",
            "fixture-snu-professor",
            "Fixture Vision Lab",
            "Fixture Han",
            "Fixture Computer Science",
            "Computer Vision",
        ),
        (
            "fixture-multimodal-lab",
            "fixture-kaist-professor",
            "Fixture Multimodal Lab",
            "Fixture Min",
            "Fixture AI Graduate School",
            "Multimodal AI",
        ),
        (
            "fixture-robotics-lab",
            "fixture-postech-professor",
            "Fixture Robotics Lab",
            "Fixture Park",
            "Fixture Computer Science",
            "Robotics",
        ),
    )
    for lab_id, professor_id, name, professor_name, department, field in labs:
        add_if_missing(
            session,
            Lab,
            lab_id,
            id=lab_id,
            professor_id=professor_id,
            name=name,
            professor_name=professor_name,
            department=department,
            field=field,
            location="Fixture campus",
            summary_text="Fictional fixture data for local development only.",
            summary_origin="fixture",
            source_url=FIXTURE_SOURCE_URL,
            source_checked_at=FIXTURE_CHECKED_AT,
        )

    for lab_id, keyword_id in (
        ("fixture-vision-lab", "fixture-computer-vision"),
        ("fixture-vision-lab", "fixture-multimodal"),
        ("fixture-multimodal-lab", "fixture-multimodal"),
        ("fixture-multimodal-lab", "fixture-ml-systems"),
        ("fixture-robotics-lab", "fixture-robotics"),
    ):
        add_if_missing(
            session, LabKeyword, (lab_id, keyword_id), lab_id=lab_id, keyword_id=keyword_id
        )

    add_if_missing(
        session,
        User,
        "demo-user",
        id="demo-user",
        email="demo-user@fixture.example.invalid",
    )
    add_if_missing(
        session,
        UserProfile,
        "demo-user",
        user_id="demo-user",
        name="Fixture User",
        affiliation="Fixture Science University",
        status="student",
        program="Fixture Computer Science Department",
        interests_json=["컴퓨터 비전", "Multimodal"],
    )
    for keyword_id in ("fixture-computer-vision", "fixture-multimodal"):
        add_if_missing(
            session,
            UserKeyword,
            ("demo-user", keyword_id),
            user_id="demo-user",
            keyword_id=keyword_id,
        )
    add_if_missing(
        session,
        LabFact,
        "fixture-vision-keyword",
        id="fixture-vision-keyword",
        lab_id="fixture-vision-lab",
        fact_type="keyword",
        value_text="fixture computer vision",
        origin="fixture",
        source_url=FIXTURE_SOURCE_URL,
        source_checked_at=FIXTURE_CHECKED_AT,
    )
    add_if_missing(
        session,
        Paper,
        "fixture-paper-001",
        id="fixture-paper-001",
        lab_id="fixture-vision-lab",
        title="Fixture Paper: Not a Real Publication",
        venue="Fixture Venue",
        published_year=2026,
        external_id="fixture-001",
        keywords_json=["fixture", "computer vision"],
        source_url=FIXTURE_SOURCE_URL,
        source_checked_at=FIXTURE_CHECKED_AT,
        last_crawled_at=FIXTURE_CHECKED_AT,
    )
    session.flush()
    add_if_missing(
        session,
        Favorite,
        ("demo-user", "fixture-vision-lab"),
        user_id="demo-user",
        lab_id="fixture-vision-lab",
    )
    add_if_missing(
        session,
        Recommendation,
        "fixture-recommendation-vision",
        id="fixture-recommendation-vision",
        user_id="demo-user",
        lab_id="fixture-vision-lab",
        keyword_score=94,
        semantic_score=82,
        research_score=78,
        preference_score=88,
        total_score=87,
        confidence=75,
        reason="Fixture recommendation for testing score ordering and explanation display.",
        score_breakdown={"origin": "fixture", "version": "fixture-v1"},
    )
    add_if_missing(
        session,
        Recommendation,
        "fixture-recommendation-multimodal",
        id="fixture-recommendation-multimodal",
        user_id="demo-user",
        lab_id="fixture-multimodal-lab",
        keyword_score=85,
        semantic_score=90,
        research_score=81,
        preference_score=76,
        total_score=84,
        confidence=70,
        reason="Fixture recommendation; it is not a real admission or research assessment.",
        score_breakdown={"origin": "fixture", "version": "fixture-v1"},
    )
    add_if_missing(
        session,
        AdmissionEvent,
        "fixture-postech-admission-event",
        id="fixture-postech-admission-event",
        university_id="fixture-postech",
        title="Fixture Graduate Admission Timeline",
        event_date=date(2026, 9, 1),
        source_url=FIXTURE_SOURCE_URL,
        source_checked_at=FIXTURE_CHECKED_AT,
        origin="fixture",
    )
    session.flush()
    add_if_missing(
        session,
        CrawlSource,
        "fixture-vision-source",
        id="fixture-vision-source",
        base_url="https://example.invalid/ddacksaeu-fixtures/vision",
        source_type="fixture",
        lab_id="fixture-vision-lab",
        professor_id="fixture-snu-professor",
        is_active=False,
        last_crawled_at=FIXTURE_CHECKED_AT,
    )
    add_if_missing(
        session,
        CrawlRun,
        "fixture-crawl-run-001",
        id="fixture-crawl-run-001",
        source_id="fixture-vision-source",
        status="succeeded",
        started_at=FIXTURE_CHECKED_AT,
        completed_at=FIXTURE_CHECKED_AT,
        discovered_count=1,
        saved_count=1,
    )
    session.commit()


def main() -> None:
    session = get_session_factory()()
    try:
        seed_database(session)
    finally:
        session.close()
    print("Fixture seed complete. No real personal, research, or admission data was inserted.")


if __name__ == "__main__":
    main()
