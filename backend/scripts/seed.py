from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.models import Lab, LabFact, Paper, User, UserProfile

FIXTURE_SOURCE_URL = "https://example.invalid/ddacksaeu-fixtures"
FIXTURE_CHECKED_AT = datetime(2026, 7, 18, tzinfo=UTC)


def seed_database(session: Session) -> None:
    """Insert explicitly fictional fixture records without duplicating stable IDs."""
    if session.get(User, "demo-user") is None:
        session.add(User(id="demo-user"))
    if session.get(UserProfile, "demo-user") is None:
        session.add(
            UserProfile(
                user_id="demo-user",
                name="Fixture User",
                affiliation="Fixture Science University",
                status="student",
                program="Fixture Computer Science Department",
                interests_json=["fixture keyword"],
            )
        )

    lab_id = "fixture-vision-lab"
    if session.get(Lab, lab_id) is None:
        session.add(
            Lab(
                id=lab_id,
                name="Fixture Vision Lab",
                professor_name="Fixture Professor",
                department="Fixture Science University / Computer Science Department",
                field="Computer Vision",
                location="Fixture Science University",
                summary_text="Fictional fixture data for local development only.",
                summary_origin="fixture",
                source_url=FIXTURE_SOURCE_URL,
                source_checked_at=FIXTURE_CHECKED_AT,
            )
        )
    if session.get(LabFact, "fixture-vision-keyword") is None:
        session.add(
            LabFact(
                id="fixture-vision-keyword",
                lab_id=lab_id,
                fact_type="keyword",
                value_text="fixture computer vision",
                origin="fixture",
                source_url=FIXTURE_SOURCE_URL,
                source_checked_at=FIXTURE_CHECKED_AT,
            )
        )
    if session.get(Paper, "fixture-paper-001") is None:
        session.add(
            Paper(
                id="fixture-paper-001",
                lab_id=lab_id,
                title="Fixture Paper: Not a Real Publication",
                venue="Fixture Venue",
                published_year=2026,
                keywords_json=["fixture", "computer vision"],
                source_url=FIXTURE_SOURCE_URL,
                source_checked_at=FIXTURE_CHECKED_AT,
            )
        )
    session.commit()


def main() -> None:
    session = get_session_factory()()
    try:
        seed_database(session)
    finally:
        session.close()
    print(
        "Fixture seed complete. No real institution, professor, email, or paper data was inserted."
    )


if __name__ == "__main__":
    main()
