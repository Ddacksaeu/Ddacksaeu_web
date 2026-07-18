from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import DocumentAnalysis, UploadedDocument
from app.schemas.documents import StructuredDocumentAnalysis
from app.services.document_analysis import service


def _analysis() -> StructuredDocumentAnalysis:
    return StructuredDocumentAnalysis(
        education=["B.S. in Computer Science"],
        skills=["Python", "PyTorch"],
        projects=[
            {
                "name": "Vision project",
                "description": "Built an image classifier",
                "technologies": ["PyTorch"],
            }
        ],
        research_experience=["Computer vision research assistant"],
        research_interests=["Computer vision"],
        strengths=["Strong implementation experience"],
        missing_information=["Publication links"],
        keywords=["computer vision", "pytorch"],
        keyword_weights={"computer vision": 0.9, "pytorch": 0.7},
        short_summary="Computer vision candidate with practical PyTorch experience.",
    )


def _upload(client: TestClient):
    return client.post(
        "/api/v1/documents/analyze",
        data={"user_id": "test-user"},
        files={"file": ("cv.pdf", b"%PDF-1.7 test", "application/pdf")},
    )


def test_analyze_pdf_persists_supported_fields_and_returns_structured_result(
    client: TestClient, session_factory: sessionmaker[Session], tmp_path, monkeypatch
) -> None:
    client.app.state.settings.document_upload_dir = str(tmp_path / "private-uploads")
    monkeypatch.setattr(
        "app.api.v1.documents.extract_pdf_text",
        lambda *_: "A sufficiently long extracted CV text. " * 10,
    )
    monkeypatch.setattr("app.api.v1.documents.analyze_document_text", lambda *_, **__: _analysis())

    response = _upload(client)

    assert response.status_code == 201
    payload = response.json()
    assert payload["education"] == ["B.S. in Computer Science"]
    assert payload["keyword_weights"] == {"computer vision": 0.9, "pytorch": 0.7}
    with session_factory() as session:
        document = session.scalar(select(UploadedDocument))
        analysis = session.scalar(select(DocumentAnalysis))
    assert document is not None and document.status == "completed"
    assert analysis is not None
    assert analysis.skills_json == ["Python", "PyTorch"]
    assert analysis.methodologies_json == ["Computer vision"]
    assert (tmp_path / "private-uploads" / document.storage_key).is_file()


def test_rejects_scanned_pdf_before_openai_call(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.documents.extract_pdf_text",
        lambda *_: (_ for _ in ()).throw(
            service.DocumentProcessingError("scanned_pdf", 422, "No text")
        ),
    )

    response = _upload(client)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "scanned_pdf"


def test_openai_structured_output_client_is_mocked(monkeypatch) -> None:
    parsed = _analysis()
    fake_client = SimpleNamespace(
        beta=SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    parse=lambda **_: SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed))]
                    )
                )
            )
        )
    )
    monkeypatch.setattr(service, "get_openai_client", lambda *_: fake_client)

    result = service.analyze_document_text(
        "Enough CV text", api_key="test-key", model="test-model", timeout_seconds=1
    )

    assert result == parsed


def test_invalid_openai_structured_output_is_handled(monkeypatch) -> None:
    fake_client = SimpleNamespace(
        beta=SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    parse=lambda **_: SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(parsed=None))]
                    )
                )
            )
        )
    )
    monkeypatch.setattr(service, "get_openai_client", lambda *_: fake_client)

    try:
        service.analyze_document_text(
            "Enough CV text", api_key="test-key", model="test-model", timeout_seconds=1
        )
    except service.DocumentProcessingError as error:
        assert error.code == "invalid_openai_response"
    else:
        raise AssertionError("Expected structured output failure")
