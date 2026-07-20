from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Department,
    ImportBatch,
    Keyword,
    Lab,
    LabKeyword,
    Paper,
    Professor,
    University,
)
from app.services.recommendation.normalization import normalize_term

POSTECH_ID = "postech"
POSTECH_NAME = "Pohang University of Science and Technology"
DEFAULT_MAX_PUBLICATIONS_PER_LAB = 10


@dataclass(frozen=True)
class NormalizedLab:
    id: str
    professor_id: str
    professor_name: str
    department_id: str
    department_name: str
    name: str
    field: str
    homepage_url: str | None
    profile_url: str | None
    email: str | None
    location: str | None
    summary: str | None
    keywords: tuple[str, ...]
    source_url: str
    fetched_at: datetime | None


@dataclass(frozen=True)
class NormalizedPaper:
    id: str
    lab_id: str
    external_id: str
    title: str
    venue: str
    year: int
    paper_url: str | None
    source_url: str
    fetched_at: datetime | None
    keywords: tuple[str, ...] = ()


@dataclass
class ImportReport:
    batch_id: str
    dry_run: bool
    created: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    updated: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    skipped: list[dict[str, str]] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)

    def payload(self) -> dict:
        return asdict(self)


def _value(row: dict[str, str], key: str) -> str | None:
    value = (row.get(key) or "").strip()
    return value or None


def _timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _url(value: str | None) -> bool:
    if not value:
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _keywords(value: str | None) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.strip() for item in (value or "").split(";") if item.strip()))


def normalize_labs(rows: list[dict[str, str]]) -> list[NormalizedLab]:
    normalized: list[NormalizedLab] = []
    for row in rows:
        lab_id, professor_id = _value(row, "lab_id"), _value(row, "researcher_id")
        name, professor = (
            _value(row, "lab_name_kor") or _value(row, "lab_name_eng"),
            _value(row, "professor_name"),
        )
        department_id, department = _value(row, "department_id"), _value(row, "department_name")
        source = _value(row, "source_url") or _value(row, "professor_profile_url")
        if not all((lab_id, professor_id, name, professor, department_id, department, source)):
            continue
        normalized.append(
            NormalizedLab(
                id=lab_id,
                professor_id=professor_id,
                professor_name=professor,
                department_id=department_id,
                department_name=department,
                name=name,
                field=_value(row, "primary_field") or "Unclassified",
                homepage_url=_value(row, "lab_url"),
                profile_url=_value(row, "professor_profile_url"),
                email=_value(row, "email"),
                location=_value(row, "location"),
                summary=_value(row, "research_summary"),
                keywords=_keywords(_value(row, "keywords")),
                source_url=source,
                fetched_at=_timestamp(_value(row, "enriched_at") or _value(row, "crawled_at")),
            )
        )
    return normalized


def normalize_papers(rows: list[dict[str, str]]) -> list[NormalizedPaper]:
    normalized: list[NormalizedPaper] = []
    for row in rows:
        if _value(row, "output_type") != "publication":
            continue
        output_id, lab_id, title = (
            _value(row, "output_id"),
            _value(row, "lab_id"),
            _value(row, "title"),
        )
        source = _value(row, "source_url")
        try:
            year = int(_value(row, "year") or "")
        except ValueError:
            continue
        if not all((output_id, lab_id, title, source)):
            continue
        normalized.append(
            NormalizedPaper(
                id=output_id,
                lab_id=lab_id,
                external_id=_value(row, "identifier") or output_id,
                title=title,
                venue=_value(row, "venue_or_organization") or "POSTECH research output",
                year=year,
                paper_url=_value(row, "url"),
                source_url=source,
                fetched_at=_timestamp(_value(row, "crawled_at")),
            )
        )
    return normalized


def validate_lab(record: NormalizedLab, seen: set[tuple[str, str]]) -> str | None:
    if not record.professor_name or not record.name:
        return "missing professor or lab name"
    if not record.department_name:
        return "missing department"
    if not _url(record.homepage_url) or not _url(record.profile_url) or not _url(record.source_url):
        return "invalid lab, profile, or source URL"
    key = (normalize_term(record.professor_name), normalize_term(record.name))
    if key in seen:
        return "duplicate professor/lab pair"
    seen.add(key)
    return None


def validate_paper(record: NormalizedPaper, lab_ids: set[str]) -> str | None:
    if record.lab_id not in lab_ids:
        return "paper references an excluded or missing lab"
    if not record.title or not (1900 <= record.year <= datetime.now(UTC).year + 1):
        return "missing title or invalid publication year"
    if not _url(record.paper_url) or not _url(record.source_url):
        return "invalid paper or source URL"
    return None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def research_outputs_path(data_dir: Path) -> Path:
    """Prefer the crawler's validated publication export when it is available."""
    cleaned = data_dir / "research_outputs_clean.csv"
    return cleaned if cleaned.is_file() else data_dir / "research_outputs.csv"


def _keyword_id(term: str) -> str:
    return "postech-keyword-" + hashlib.sha1(normalize_term(term).encode()).hexdigest()[:20]


def _upsert(
    session: Session, model, identifier: str, values: dict, report: ImportReport, name: str
):
    row = session.get(model, identifier)
    if row is None:
        row = model(id=identifier, **values)
        session.add(row)
        report.created[name] += 1
    else:
        for key, value in values.items():
            setattr(row, key, value)
        report.updated[name] += 1
    return row


def import_postech(
    session: Session,
    data_dir: Path,
    *,
    dry_run: bool = False,
    max_publications_per_lab: int = DEFAULT_MAX_PUBLICATIONS_PER_LAB,
    include_all_publications: bool = False,
) -> ImportReport:
    batch_id = str(uuid4())
    report = ImportReport(batch_id=batch_id, dry_run=dry_run)
    raw_labs = read_csv(data_dir / "labs.csv")
    raw_papers = read_csv(research_outputs_path(data_dir))
    labs = normalize_labs(raw_labs)
    papers = normalize_papers(raw_papers)
    normalized_lab_ids = {item.id for item in labs}
    for index, row in enumerate(raw_labs, start=2):
        raw_id = _value(row, "lab_id")
        if raw_id not in normalized_lab_ids:
            report.skipped.append(
                {
                    "record": raw_id or f"labs.csv:{index}",
                    "reason": "missing required lab mapping fields",
                }
            )
    normalized_paper_ids = {item.id for item in papers}
    for index, row in enumerate(raw_papers, start=2):
        raw_id = _value(row, "output_id")
        if raw_id not in normalized_paper_ids:
            reason = (
                "non-publication research output is not used by the recommendation MVP"
                if _value(row, "output_type") != "publication"
                else "missing required paper mapping fields or invalid year"
            )
            report.skipped.append(
                {
                    "record": raw_id or f"research_outputs.csv:{index}",
                    "reason": reason,
                }
            )
    seen: set[tuple[str, str]] = set()
    valid_labs: list[NormalizedLab] = []
    for item in labs:
        reason = validate_lab(item, seen)
        if reason:
            report.skipped.append({"record": item.id, "reason": reason})
        else:
            valid_labs.append(item)
    valid_ids = {item.id for item in valid_labs}
    publications_by_lab: dict[str, list[NormalizedPaper]] = defaultdict(list)
    for item in papers:
        reason = validate_paper(item, valid_ids)
        if reason:
            report.skipped.append({"record": item.id, "reason": reason})
        else:
            publications_by_lab[item.lab_id].append(item)
    selected_papers = [
        paper
        for values in publications_by_lab.values()
        for paper in sorted(values, key=lambda value: (-value.year, value.id))[
            : None if include_all_publications else max_publications_per_lab
        ]
    ]
    if dry_run:
        report.created.update(
            {
                "universities": 1,
                "departments": len({x.department_id for x in valid_labs}),
                "professors": len({x.professor_id for x in valid_labs}),
                "labs": len(valid_labs),
                "papers": len(selected_papers),
            }
        )
        return report
    batch = ImportBatch(
        id=batch_id, source_type="postech_csv", source_path=str(data_dir), status="running"
    )
    session.add(batch)
    try:
        _upsert(
            session,
            University,
            POSTECH_ID,
            {
                "name": POSTECH_NAME,
                "country": "KR",
                "source_url": "https://www.postech.ac.kr/",
                "source_checked_at": datetime.now(UTC),
            },
            report,
            "universities",
        )
        departments_by_id: dict[str, Department] = {}
        professors_by_id: dict[str, Professor] = {}
        labs_by_id: dict[str, Lab] = {}
        keywords_by_normalized: dict[str, Keyword] = {}
        for item in valid_labs:
            if item.department_id not in departments_by_id:
                departments_by_id[item.department_id] = _upsert(
                    session,
                    Department,
                    item.department_id,
                    {"university_id": POSTECH_ID, "name": item.department_name},
                    report,
                    "departments",
                )
            if item.professor_id not in professors_by_id:
                professors_by_id[item.professor_id] = _upsert(
                    session,
                    Professor,
                    item.professor_id,
                    {
                        "university_id": POSTECH_ID,
                        "department_id": item.department_id,
                        "name": item.professor_name,
                        "profile_url": item.profile_url,
                        "source_url": item.source_url,
                        "source_checked_at": item.fetched_at,
                    },
                    report,
                    "professors",
                )
            lab = labs_by_id.get(item.id)
            if lab is None:
                lab = _upsert(
                    session,
                    Lab,
                    item.id,
                    {
                        "professor_id": item.professor_id,
                        "name": item.name,
                        "professor_name": item.professor_name,
                        "department": item.department_name,
                        "field": item.field,
                        "homepage_url": item.homepage_url,
                        "location": item.location,
                        "contact_email": item.email,
                        "summary_text": item.summary,
                        "summary_origin": "source",
                        "source_url": item.source_url,
                        "source_checked_at": item.fetched_at,
                        "source_type": "postech_csv",
                        "import_batch_id": batch_id,
                        "validation_status": "valid",
                    },
                    report,
                    "labs",
                )
                labs_by_id[item.id] = lab
            for term in item.keywords:
                normalized = normalize_term(term)
                if not normalized:
                    continue
                keyword = keywords_by_normalized.get(normalized)
                if keyword is None:
                    keyword = session.scalar(
                        select(Keyword).where(Keyword.normalized_term == normalized)
                    )
                if keyword is None:
                    keyword = Keyword(
                        id=_keyword_id(term), term_ko=term, term_en=None, normalized_term=normalized
                    )
                    session.add(keyword)
                    report.created["keywords"] += 1
                keywords_by_normalized[normalized] = keyword
                if not session.get(LabKeyword, {"lab_id": lab.id, "keyword_id": keyword.id}):
                    session.add(LabKeyword(lab_id=lab.id, keyword_id=keyword.id))
        session.flush()
        for item in selected_papers:
            _upsert(
                session,
                Paper,
                item.id,
                {
                    "lab_id": item.lab_id,
                    "title": item.title,
                    "venue": item.venue,
                    "published_year": item.year,
                    "abstract": None,
                    "summary": None,
                    "external_id": item.external_id,
                    "keywords_json": list(item.keywords),
                    "paper_url": item.paper_url,
                    "source_url": item.source_url,
                    "source_checked_at": item.fetched_at,
                    "last_crawled_at": item.fetched_at,
                    "source_type": "postech_csv",
                    "import_batch_id": batch_id,
                    "validation_status": "valid",
                },
                report,
                "papers",
            )
        batch.status = "completed"
    except Exception as error:
        batch.status = "failed"
        report.errors.append({"record": "batch", "reason": str(error)})
        raise
    finally:
        batch.completed_at = datetime.now(UTC)
        batch.report_json = report.payload()
    return report


def write_report(report: ImportReport, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"postech-import-{report.batch_id}.json"
    path.write_text(json.dumps(report.payload(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
