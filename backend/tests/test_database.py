from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import User


def test_sqlite_test_database_session(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(User(id="session-test"))
        session.commit()

    with session_factory() as session:
        assert session.scalar(select(User).where(User.id == "session-test")).id == "session-test"
