from __future__ import annotations

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
    account = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "cv-owner@example.com",
            "password": "secure-password-123",
            "name": "CV owner",
        },
    ).json()
    return client.post(
        "/api/v1/documents/analyze",
        headers={"Authorization": f"Bearer {account['access_token']}"},
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
    assert payload["education"][0]["degree"] == "B.S. in Computer Science"
    assert payload["keyword_weights"] == {"computer vision": 0.9, "pytorch": 0.7}
    with session_factory() as session:
        document = session.scalar(select(UploadedDocument))
        analysis = session.scalar(select(DocumentAnalysis))
    assert document is not None and document.status == "completed"
    assert analysis is not None
    assert analysis.skills_json == ["Python", "PyTorch"]
    assert analysis.methodologies_json == ["Computer vision"]
    assert (tmp_path / "private-uploads" / document.storage_key).is_file()


def test_rejects_scanned_pdf_before_local_analysis(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.documents.extract_pdf_text",
        lambda *_: (_ for _ in ()).throw(
            service.DocumentProcessingError("scanned_pdf", 422, "No text")
        ),
    )

    response = _upload(client)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "scanned_pdf"


def test_local_analysis_is_deterministic_without_api_key() -> None:
    text = """Education
B.S. Computer Science | Example University | 2022 - 2026
Research Experience
Vision Research Assistant | Example Lab | 2025 - Present
- Trained a PyTorch object detection model on 10,000 images
Projects
Campus Vision Project | 2025
- Built a Computer Vision prototype with Python and PyTorch
Work Experience
Software Engineering Intern | Example Company | 2024 - 2025
- Implemented a FastAPI service with PostgreSQL
Campus & Community Involvement
Robotics Club Mentor | Example University | 2023 - Present
- Mentored 20 students and organized weekly workshops
Skills
Python, PyTorch, FastAPI, PostgreSQL, Computer Vision
"""
    first = service.analyze_document_text(text)
    second = service.analyze_document_text(text)

    assert first == second
    assert "Python" in first.skills
    assert "Computer Vision" in first.research_interests
    assert first.keywords
    assert first.education[0].institution == "Example University"
    assert first.research_experience[0].details
    assert first.projects[0].name == "Campus Vision Project"
    assert first.work_experience[0].title == "Software Engineering Intern"
    assert first.campus_community_involvement[0].title == "Robotics Club Mentor"
    assert "FastAPI" in first.skills


def test_latest_analysis_is_authenticated_and_user_isolated(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(
        "app.api.v1.documents.extract_txt_text",
        lambda *_: "Computer Vision Python PyTorch research project " * 5,
    )
    first = client.post(
        "/api/v1/auth/signup",
        json={"email": "first-cv@example.com", "password": "secure-password-123", "name": "First"},
    ).json()
    second = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "second-cv@example.com",
            "password": "secure-password-123",
            "name": "Second",
        },
    ).json()
    headers = {"Authorization": f"Bearer {first['access_token']}"}
    uploaded = client.post(
        "/api/v1/documents/analyze",
        headers=headers,
        files={
            "file": (
                "cv.txt",
                b"Computer Vision Python PyTorch research project " * 5,
                "text/plain",
            )
        },
    )

    assert uploaded.status_code == 201
    assert uploaded.json()["analyzer_origin"] == "local_rule_based"
    assert client.get("/api/v1/documents/latest", headers=headers).status_code == 200
    assert (
        client.get("/api/v1/documents", headers=headers).json()[0]["document_id"]
        == uploaded.json()["document_id"]
    )
    assert (
        client.get(
            "/api/v1/documents/latest",
            headers={"Authorization": f"Bearer {second['access_token']}"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/documents/analyze", files={"file": ("cv.txt", b"text", "text/plain")}
        ).status_code
        == 401
    )


def test_txt_and_invalid_upload_validation(client: TestClient) -> None:
    account = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "validation@example.com",
            "password": "secure-password-123",
            "name": "Validation",
        },
    ).json()
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    assert (
        client.post(
            "/api/v1/documents/analyze",
            headers=headers,
            files={"file": ("bad.exe", b"x" * 600, "application/octet-stream")},
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/api/v1/documents/analyze",
            headers=headers,
            files={"file": ("empty.txt", b"", "text/plain")},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/documents/analyze",
            headers=headers,
            files={"file": ("image.pdf", b"%PDF-1.7\n", "application/pdf")},
        ).status_code
        == 422
    )
