from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO

from app.schemas.documents import EvidenceItem, ProjectAnalysis, StructuredDocumentAnalysis


@dataclass(frozen=True)
class DocumentProcessingError(Exception):
    code: str
    status_code: int
    message: str


def get_openai_client(api_key: str, timeout_seconds: float):
    """Legacy recommendation helper; the local CV analyzer never calls this."""
    from openai import OpenAI

    return OpenAI(api_key=api_key, timeout=timeout_seconds)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).replace("\x00", " ")).strip()


def extract_pdf_text(content: bytes, minimum_characters: int) -> str:
    try:
        from pypdf import PdfReader

        text = normalize_text(
            "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
        )
    except Exception as exc:
        raise DocumentProcessingError("invalid_pdf", 422, "The file is not a readable PDF") from exc
    if not text:
        raise DocumentProcessingError(
            "scanned_pdf", 422, "No selectable text was found; this PDF requires OCR"
        )
    if len(text) < minimum_characters:
        raise DocumentProcessingError(
            "insufficient_text", 422, "The extracted text is too short to analyze"
        )
    return text


def extract_docx_text(content: bytes, minimum_characters: int) -> str:
    try:
        from docx import Document

        text = normalize_text(
            "\n".join(paragraph.text for paragraph in Document(BytesIO(content)).paragraphs)
        )
    except Exception as exc:
        raise DocumentProcessingError(
            "invalid_docx", 422, "The file is not a readable DOCX"
        ) from exc
    if len(text) < minimum_characters:
        raise DocumentProcessingError(
            "insufficient_text", 422, "The extracted text is too short to analyze"
        )
    return text


def extract_txt_text(content: bytes, minimum_characters: int) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            text = normalize_text(content.decode(encoding))
            break
        except UnicodeDecodeError:
            continue
    else:
        raise DocumentProcessingError(
            "invalid_text", 422, "The text file encoding is not supported"
        )
    if len(text) < minimum_characters:
        raise DocumentProcessingError(
            "insufficient_text", 422, "The extracted text is too short to analyze"
        )
    return text


class CvAnalyzer:
    def analyze(self, text: str) -> StructuredDocumentAnalysis:  # pragma: no cover - interface
        raise NotImplementedError


class LocalRuleBasedCvAnalyzer(CvAnalyzer):
    terms = (
        "Python",
        "PyTorch",
        "TensorFlow",
        "scikit-learn",
        "SQL",
        "Docker",
        "Computer Vision",
        "Machine Learning",
        "NLP",
        "Robotics",
        "HCI",
        "Deep Learning",
    )

    def analyze(self, text: str) -> StructuredDocumentAnalysis:
        lines = [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]
        lower = text.lower()
        found = [term for term in self.terms if term.lower() in lower]
        education = [
            line
            for line in lines
            if re.search(
                r"\b(B\.?S\.?|M\.?S\.?|Ph\.?D|Bachelor|Master|University|대학교)\b", line, re.I
            )
        ][:5]
        projects = [
            ProjectAnalysis(
                name=line[:120],
                description=line[:500],
                technologies=[term for term in found if term.lower() in line.lower()],
            )
            for line in lines
            if re.search(r"\b(project|thesis|research|publication|논문|프로젝트)\b", line, re.I)
        ][:8]
        interests = [
            term
            for term in found
            if term
            in {"Computer Vision", "Machine Learning", "NLP", "Robotics", "HCI", "Deep Learning"}
        ]
        keywords = sorted(found, key=lambda term: (-lower.count(term.lower()), term.lower()))[:12]
        evidence = {
            "skills": [
                EvidenceItem(
                    value=term,
                    confidence=min(1.0, round(0.5 + lower.count(term.lower()) * 0.1, 2)),
                    evidence=next((line for line in lines if term.lower() in line.lower()), term),
                )
                for term in found
            ],
            "research_interests": [
                EvidenceItem(
                    value=term,
                    confidence=0.8,
                    evidence=next((line for line in lines if term.lower() in line.lower()), term),
                )
                for term in interests
            ],
        }
        return StructuredDocumentAnalysis(
            education=education,
            skills=found,
            projects=projects,
            research_experience=[
                line for line in lines if "research" in line.lower() or "연구" in line
            ][:5],
            research_interests=interests,
            strengths=keywords[:3],
            missing_information=[],
            keywords=keywords,
            keyword_weights={
                term: min(1.0, round(0.5 + lower.count(term.lower()) * 0.1, 2)) for term in keywords
            },
            short_summary=f"Local rule-based analysis found {len(keywords)} relevant keywords.",
            evidence_items=evidence,
        )


def analyze_document_text(text: str, **_: object) -> StructuredDocumentAnalysis:
    return LocalRuleBasedCvAnalyzer().analyze(text)
