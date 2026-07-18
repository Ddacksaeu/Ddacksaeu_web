from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db_session
from app.repositories.documents import (
    create_completed_analysis,
    create_failed_analysis,
    create_uploaded_document,
)
from app.schemas.documents import DocumentAnalysisResponse
from app.services.document_analysis import (
    DocumentProcessingError,
    analyze_document_text,
    extract_pdf_text,
)

router = APIRouter(prefix="/documents", tags=["documents"])
_USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _error_response(request: Request, error: DocumentProcessingError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": error.code, "message": error.message}},
        headers={"X-Request-ID": request.state.request_id},
    )


def _validate_upload(file: UploadFile, content: bytes, settings: Settings) -> None:
    filename = file.filename or ""
    if len(filename) > 255:
        raise DocumentProcessingError("invalid_filename", 422, "The filename is too long")
    if not filename.lower().endswith(".pdf") or file.content_type not in {
        "application/pdf",
        "application/x-pdf",
    }:
        raise DocumentProcessingError("invalid_file_type", 415, "Only PDF files are supported")
    if len(content) > settings.document_max_upload_bytes:
        raise DocumentProcessingError(
            "file_too_large", 413, "The PDF exceeds the upload size limit"
        )
    if not content:
        raise DocumentProcessingError("empty_pdf", 422, "The PDF is empty")
    if not content.startswith(b"%PDF-"):
        raise DocumentProcessingError("invalid_pdf", 422, "The file is not a PDF")


def _save_private_upload(root: Path, storage_key: str, content: bytes) -> None:
    destination = root.resolve() / storage_key
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as upload_file:
        upload_file.write(content)


@router.post("/analyze", response_model=DocumentAnalysisResponse, status_code=201)
def analyze_document(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    user_id: str = Form(...),
    db: Session = Depends(get_db_session),  # noqa: B008
) -> DocumentAnalysisResponse | JSONResponse:
    settings: Settings = request.app.state.settings
    document = None
    try:
        if not _USER_ID_PATTERN.fullmatch(user_id):
            raise DocumentProcessingError("invalid_user_id", 422, "Invalid user ID")
        content = file.file.read(settings.document_max_upload_bytes + 1)
        _validate_upload(file, content, settings)
        extracted_text = extract_pdf_text(content, settings.document_min_extracted_characters)
        document = create_uploaded_document(
            db,
            user_id=user_id,
            filename=file.filename or "document.pdf",
            content_type="application/pdf",
            byte_size=len(content),
        )
        _save_private_upload(Path(settings.document_upload_dir), document.storage_key, content)
        result = analyze_document_text(
            extracted_text,
            api_key=(
                settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
            ),
            model=settings.openai_model,
            timeout_seconds=settings.openai_timeout_seconds,
        )
        analysis = create_completed_analysis(db, document=document, result=result)
        return DocumentAnalysisResponse(
            document_id=document.id,
            analysis_id=analysis.id,
            **result.model_dump(),
        )
    except DocumentProcessingError as error:
        if document is not None:
            create_failed_analysis(db, document=document, error_code=error.code)
        return _error_response(request, error)
    finally:
        file.file.close()
