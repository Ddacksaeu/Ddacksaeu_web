from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from pydantic import ValidationError

from app.schemas.documents import StructuredDocumentAnalysis

SYSTEM_PROMPT = """Analyze the supplied CV or portfolio. Extract only facts supported by the text.
Use empty lists when information is absent. `keyword_weights` values must be between 0 and 1.
Do not infer protected attributes. Write the short summary in the document's primary language."""


@dataclass(frozen=True)
class DocumentProcessingError(Exception):
    code: str
    status_code: int
    message: str


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\x00", " ")
    return re.sub(r"\s+", " ", text).strip()


def extract_pdf_text(pdf_bytes: bytes, minimum_characters: int) -> str:
    if not pdf_bytes:
        raise DocumentProcessingError("empty_pdf", 422, "The PDF is empty")
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(pdf_bytes))
        if not reader.pages:
            raise DocumentProcessingError("empty_pdf", 422, "The PDF has no pages")
        text = normalize_text("\n".join(page.extract_text() or "" for page in reader.pages))
    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError("invalid_pdf", 422, "The file is not a readable PDF") from exc
    if not text:
        raise DocumentProcessingError(
            "scanned_pdf", 422, "No selectable text was found; upload a text-based PDF"
        )
    if len(text) < minimum_characters:
        raise DocumentProcessingError(
            "insufficient_text", 422, "The extracted text is too short to analyze"
        )
    return text


def get_openai_client(api_key: str, timeout_seconds: float) -> Any:
    from openai import OpenAI

    return OpenAI(api_key=api_key, timeout=timeout_seconds)


def analyze_document_text(
    text: str, *, api_key: str | None, model: str, timeout_seconds: float
) -> StructuredDocumentAnalysis:
    if not api_key:
        raise DocumentProcessingError(
            "openai_not_configured", 503, "Analysis service is unavailable"
        )
    try:
        completion = get_openai_client(api_key, timeout_seconds).beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text[:50_000]},
            ],
            response_format=StructuredDocumentAnalysis,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise DocumentProcessingError(
                "invalid_openai_response", 502, "Analysis service returned invalid structured data"
            )
        return StructuredDocumentAnalysis.model_validate(parsed)
    except DocumentProcessingError:
        raise
    except (TimeoutError, ValidationError, IndexError, AttributeError) as exc:
        raise DocumentProcessingError(
            "openai_analysis_failed", 502, "Analysis service could not process the document"
        ) from exc
    except Exception as exc:
        if exc.__class__.__name__ == "APITimeoutError":
            raise DocumentProcessingError(
                "openai_timeout", 504, "Analysis service timed out"
            ) from exc
        raise DocumentProcessingError(
            "openai_analysis_failed", 502, "Analysis service could not process the document"
        ) from exc
