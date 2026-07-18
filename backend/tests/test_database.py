import pytest
from sqlalchemy import exc, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import CrawlRun, Favorite, Lab, LabKeyword, Recommendation, User, UserKeyword
from scripts.seed import seed_database


def test_sqlite_test_database_session(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(User(id="session-test"))
        session.commit()

    with session_factory() as session:
        assert session.scalar(select(User).where(User.id == "session-test")).id == "session-test"


def test_normalized_relationships_and_unique_constraints(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        seed_database(session)
        assert session.get(Lab, "fixture-vision-lab").professor_id == "fixture-snu-professor"

        session.add(Favorite(user_id="demo-user", lab_id="fixture-vision-lab"))
        with pytest.raises(exc.IntegrityError):
            session.commit()
        session.rollback()

        session.add(LabKeyword(lab_id="fixture-vision-lab", keyword_id="fixture-computer-vision"))
        with pytest.raises(exc.IntegrityError):
            session.commit()
        session.rollback()

        session.add(UserKeyword(user_id="demo-user", keyword_id="fixture-computer-vision"))
        with pytest.raises(exc.IntegrityError):
            session.commit()


def test_recommendation_constraints_and_crawl_status(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        seed_database(session)
        session.add(
            Recommendation(
                id="invalid-score",
                user_id="demo-user",
                lab_id="fixture-robotics-lab",
                keyword_score=101,
                semantic_score=0,
                research_score=0,
                preference_score=0,
                total_score=0,
                confidence=0,
                reason="invalid fixture",
            )
        )
        with pytest.raises(exc.IntegrityError):
            session.commit()
        session.rollback()

        session.add(
            CrawlRun(id="invalid-crawl-status", source_id="fixture-vision-source", status="unknown")
        )
        with pytest.raises(exc.IntegrityError):
            session.commit()
        session.rollback()
