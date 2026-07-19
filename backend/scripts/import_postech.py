from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import select

from app.db.session import get_session_factory
from app.importers.postech import DEFAULT_MAX_PUBLICATIONS_PER_LAB, import_postech, write_report
from app.models import Lab


def main() -> None:
    parser = argparse.ArgumentParser(description="Import validated POSTECH crawler CSV data.")
    parser.add_argument("--data-dir", type=Path, default=Path("../Crawler/data"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--max-publications-per-lab", type=int, default=DEFAULT_MAX_PUBLICATIONS_PER_LAB
    )
    parser.add_argument("--all-publications", action="store_true")
    parser.add_argument("--report-dir", type=Path, default=Path("import_reports"))
    parser.add_argument(
        "--allow-mixed", action="store_true", help="Allow fixture labs in the target database."
    )
    args = parser.parse_args()
    if args.max_publications_per_lab < 0:
        parser.error("--max-publications-per-lab must be non-negative")
    factory = get_session_factory()
    with factory() as session:
        fixture_exists = session.scalar(
            select(Lab.id).where(Lab.summary_origin == "fixture").limit(1)
        )
        if fixture_exists and not args.allow_mixed:
            parser.error(
                "target contains fixture data; use an empty DB or --allow-mixed explicitly"
            )
        report = import_postech(
            session,
            args.data_dir,
            dry_run=args.dry_run,
            max_publications_per_lab=args.max_publications_per_lab,
            include_all_publications=args.all_publications,
        )
        if not args.dry_run:
            session.commit()
        path = write_report(report, args.report_dir)
    print(report.payload())
    print(f"report: {path}")


if __name__ == "__main__":
    main()
