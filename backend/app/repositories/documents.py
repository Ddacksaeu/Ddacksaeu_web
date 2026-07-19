from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.models import DocumentAnalysis, UploadedDocument, User
from app.models.entities import new_id
from app.schemas.documents import StructuredDocumentAnalysis


def ensure_user(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id)
        db.add(user)
        db.flush()
    return user


def create_uploaded_document(
    db: Session, *, user_id: str, filename: str, content_type: str, byte_size: int
) -> UploadedDocument:
    ensure_user(db, user_id)
    document = UploadedDocument(
        id=new_id(),
        user_id=user_id,
        original_filename=filename,
        content_type=content_type,
        byte_size=byte_size,
        storage_key=f"documents/{new_id()}{Path(filename).suffix.lower()}",
        status="uploaded",
    )
    db.add(document)
    db.flush()
    return document


def create_completed_analysis(
    db: Session, *, document: UploadedDocument, result: StructuredDocumentAnalysis
) -> DocumentAnalysis:
    analysis = DocumentAnalysis(
        document_id=document.id,
        status="completed",
        keywords_json=result.keywords,
        skills_json=result.skills,
        methodologies_json=result.research_interests,
        projects_json=[project.model_dump() for project in result.projects],
        completeness=max(0, min(100, 100 - len(result.missing_information) * 10)),
        analysis_origin="local_rule_based",
    )
    document.status = "completed"
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def create_failed_analysis(db: Session, *, document: UploadedDocument, error_code: str) -> None:
    document.status = "failed"
    db.add(
        DocumentAnalysis(
            document_id=document.id,
            status="failed",
            keywords_json=[],
            skills_json=[],
            methodologies_json=[],
            projects_json=[],
            analysis_origin="local_rule_based",
            error_code=error_code,
        )
    )
    db.commit()
