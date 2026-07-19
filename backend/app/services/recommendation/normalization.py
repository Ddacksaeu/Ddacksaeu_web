from __future__ import annotations

import re
import unicodedata

ALIASES = {"ml": "machine learning", "cv": "computer vision", "ai": "artificial intelligence"}


def normalize_term(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().casefold()
    value = re.sub(r"[_-]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return ALIASES.get(value, value)


def normalize_terms(values: list[str] | tuple[str, ...]) -> list[str]:
    return sorted({term for value in values if (term := normalize_term(str(value)))})
