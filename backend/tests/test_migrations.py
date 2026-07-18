from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[1]


def test_initial_migration_upgrades_and_downgrades_sqlite(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    assert {"users", "labs", "document_analyses"}.issubset(inspect(engine).get_table_names())

    command.downgrade(config, "base")
    assert "users" not in inspect(engine).get_table_names()
    engine.dispose()
