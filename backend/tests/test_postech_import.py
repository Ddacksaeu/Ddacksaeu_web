from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.importers.postech import import_postech, normalize_labs, validate_lab
from app.models import Lab, Paper, Professor
from app.repositories.documents import create_completed_analysis, create_uploaded_document
from app.schemas.documents import StructuredDocumentAnalysis
from scripts.seed import seed_database
from tests.auth_helpers import jwt_headers


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _dataset(tmp_path: Path) -> Path:
    labs = [
        {
            "lab_id": "LAB_REAL",
            "researcher_id": "PROF_REAL",
            "department_id": "DEPT_REAL",
            "department_name": "Computer Science",
            "lab_name_kor": "Real Systems Lab",
            "lab_name_eng": "",
            "professor_name": "Real Kim",
            "primary_field": "Systems",
            "lab_url": "https://lab.postech.ac.kr",
            "professor_profile_url": "https://postech.ac.kr/p/real",
            "email": "real@postech.ac.kr",
            "location": "C5",
            "research_summary": "Reliable systems",
            "keywords": "distributed systems;databases",
            "source_url": "https://postech.ac.kr/source",
            "crawled_at": "2026-07-18T12:00:00+09:00",
            "enriched_at": "",
        },
        {
            "lab_id": "LAB_BAD",
            "researcher_id": "PROF_BAD",
            "department_id": "DEPT_REAL",
            "department_name": "Computer Science",
            "lab_name_kor": "",
            "lab_name_eng": "",
            "professor_name": "",
            "primary_field": "",
            "lab_url": "not-a-url",
            "professor_profile_url": "",
            "email": "",
            "location": "",
            "research_summary": "",
            "keywords": "",
            "source_url": "",
            "crawled_at": "",
            "enriched_at": "",
        },
        {
            "lab_id": "LAB_SHARED_KEYWORD",
            "researcher_id": "PROF_SHARED_KEYWORD",
            "department_id": "DEPT_SHARED",
            "department_name": "Electrical Engineering",
            "lab_name_kor": "Shared Keyword Lab",
            "lab_name_eng": "",
            "professor_name": "Shared Kim",
            "primary_field": "Systems",
            "lab_url": "https://shared.postech.ac.kr",
            "professor_profile_url": "https://postech.ac.kr/p/shared",
            "email": "shared@postech.ac.kr",
            "location": "C5",
            "research_summary": "Shared keyword test",
            "keywords": "distributed systems;operating systems",
            "source_url": "https://postech.ac.kr/source/shared",
            "crawled_at": "2026-07-18T12:00:00+09:00",
            "enriched_at": "",
        },
    ]
    papers = [
        {
            "output_id": f"OUT_{year}",
            "lab_id": "LAB_REAL",
            "output_type": "publication",
            "title": f"Paper {year}",
            "year": str(year),
            "venue_or_organization": "Venue",
            "identifier": f"doi-{year}",
            "url": "https://doi.org/x",
            "source_url": "https://postech.ac.kr/source",
            "crawled_at": "2026-07-18T12:00:00+09:00",
        }
        for year in (2024, 2025, 2023)
    ] + [
        {
            "output_id": "OUT_ORPHAN",
            "lab_id": "MISSING",
            "output_type": "publication",
            "title": "Orphan",
            "year": "2025",
            "venue_or_organization": "Venue",
            "identifier": "",
            "url": "https://doi.org/x",
            "source_url": "https://postech.ac.kr/source",
            "crawled_at": "2026-07-18T12:00:00+09:00",
        }
    ]
    _write_csv(tmp_path / "labs.csv", list(labs[0]), labs)
    _write_csv(tmp_path / "research_outputs.csv", list(papers[0]), papers)
    return tmp_path


def test_normalization_and_validation_reject_duplicate() -> None:
    rows = [
        {
            "lab_id": "a",
            "researcher_id": "p",
            "lab_name_kor": "Lab",
            "professor_name": "Kim",
            "department_id": "d",
            "department_name": "Dept",
            "source_url": "https://source.test",
        }
    ]
    record = normalize_labs(rows)[0]
    seen: set[tuple[str, str]] = set()
    assert validate_lab(record, seen) is None
    assert validate_lab(record, seen) == "duplicate professor/lab pair"


def test_import_is_idempotent_limits_papers_and_skips_invalid(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    data_dir = _dataset(tmp_path)
    with session_factory() as session:
        report = import_postech(session, data_dir, max_publications_per_lab=2)
        session.commit()
        assert report.created["labs"] == 2
        assert len(report.skipped) == 2
    with session_factory() as session:
        report = import_postech(session, data_dir, max_publications_per_lab=2)
        session.commit()
        assert report.updated["labs"] == 2
        assert session.scalar(select(func.count()).select_from(Lab)) == 2
        assert session.scalar(select(func.count()).select_from(Professor)) == 2
        assert session.scalar(select(func.count()).select_from(Paper)) == 2


def test_dry_run_does_not_write(session_factory: sessionmaker[Session], tmp_path: Path) -> None:
    with session_factory() as session:
        report = import_postech(session, _dataset(tmp_path), dry_run=True)
        assert report.created["labs"] == 2
        assert session.scalar(select(func.count()).select_from(Lab)) == 0


def test_imported_data_reaches_search_detail_similar_and_recommendation_apis(
    client, session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    with session_factory() as session:
        import_postech(session, _dataset(tmp_path), max_publications_per_lab=2)
        seed_database(session)
        document = create_uploaded_document(
            session,
            user_id="demo-user",
            filename="cv.txt",
            content_type="text/plain",
            byte_size=100,
        )
        create_completed_analysis(
            session,
            document=document,
            result=StructuredDocumentAnalysis(
                skills=["distributed systems"],
                research_interests=["databases"],
                keywords=["systems"],
                short_summary="test CV",
            ),
        )
    search = client.get("/api/v1/labs?q=Real%20Systems")
    assert search.status_code == 200
    assert search.json()["items"][0]["id"] == "LAB_REAL"
    assert client.get("/api/v1/labs/LAB_REAL").status_code == 200
    assert client.get("/api/v1/labs/LAB_REAL/similar").status_code == 200
    recommendations = client.get("/api/v1/recommendations", headers=jwt_headers(client))
    assert recommendations.status_code == 200
    assert any(
        item["lab_id"] == "LAB_REAL" and item["data_origin"] == "source"
        for item in recommendations.json()["items"]
    )
