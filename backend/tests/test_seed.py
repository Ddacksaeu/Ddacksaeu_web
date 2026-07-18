from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Lab, LabFact, Paper, User
from scripts.seed import seed_database


def test_fixture_seed_is_safe_to_rerun(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        seed_database(session)
        seed_database(session)

        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert session.scalar(select(func.count()).select_from(Lab)) == 1
        assert session.scalar(select(func.count()).select_from(LabFact)) == 1
        assert session.scalar(select(func.count()).select_from(Paper)) == 1
