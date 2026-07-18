from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[1]


def test_initial_migration_upgrades_and_downgrades_sqlite(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database_path = tmp_path / "migration.db"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    assert {
        "users",
        "universities",
        "departments",
        "professors",
        "keywords",
        "recommendations",
        "crawl_runs",
        "document_analyses",
    }.issubset(inspect(engine).get_table_names())
    assert {"event_type", "start_at", "is_estimated", "last_verified_at"}.issubset(
        {column["name"] for column in inspect(engine).get_columns("admission_events")}
    )

    command.downgrade(config, "20260718_0002")
    assert "event_date" in {
        column["name"] for column in inspect(engine).get_columns("admission_events")
    }
    command.upgrade(config, "head")
    assert "start_at" in {
        column["name"] for column in inspect(engine).get_columns("admission_events")
    }
    engine.dispose()
