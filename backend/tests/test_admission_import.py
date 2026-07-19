from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import func, select

from app.importers.admissions import import_admissions
from app.models import AdmissionEvent


def test_admission_import_validates_and_upserts(session_factory, tmp_path: Path) -> None:
    path = tmp_path / "admissions.json"
    path.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "id": "official-1",
                        "university_id": "postech",
                        "university_name": "POSTECH",
                        "title": "Verified deadline",
                        "event_type": "application_deadline",
                        "start_at": "2026-09-01T09:00:00+09:00",
                        "source_url": "https://postech.ac.kr/admissions",
                        "checked_at": "2026-07-19T10:00:00+09:00",
                    },
                    {"id": "bad", "title": "Invalid", "event_type": "nope"},
                ]
            }
        ),
        encoding="utf-8",
    )
    with session_factory() as session:
        report = import_admissions(session, path, dry_run=True)
        assert report.created == 1 and report.skipped[0]["record"] == "bad"
        report = import_admissions(session, path)
        session.commit()
        assert report.created == 1
    with session_factory() as session:
        report = import_admissions(session, path)
        session.commit()
        assert report.updated == 1
        assert session.scalar(select(func.count()).select_from(AdmissionEvent)) == 1
