from __future__ import annotations

import argparse
from pathlib import Path

from app.db.session import get_session_factory
from app.importers.admissions import import_admissions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import human-reviewed official admission schedules from JSON."
    )
    parser.add_argument("path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    with get_session_factory()() as session:
        report = import_admissions(session, args.path, dry_run=args.dry_run)
        if not args.dry_run:
            session.commit()
    print(
        {
            "dry_run": args.dry_run,
            "created": report.created,
            "updated": report.updated,
            "skipped": report.skipped,
        }
    )


if __name__ == "__main__":
    main()
