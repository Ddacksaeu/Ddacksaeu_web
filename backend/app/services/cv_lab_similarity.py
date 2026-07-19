from __future__ import annotations

import re
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _terms(text: str) -> list[str]:
    return sorted(set(re.findall(r"[\w가-힣]+", text.lower())))


@dataclass(frozen=True)
class CvLabSimilarity:
    similarity_score: int
    matched_keywords: list[str]
    cv_terms: list[str]
    lab_terms: list[str]


def compare_cv_to_lab(cv_text: str, lab_text: str) -> CvLabSimilarity:
    cv_terms, lab_terms = _terms(cv_text), _terms(lab_text)
    matched = sorted(set(cv_terms).intersection(lab_terms))
    if not cv_terms or not lab_terms:
        return CvLabSimilarity(0, matched, cv_terms, lab_terms)
    matrix = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b").fit_transform(
        [" ".join(cv_terms), " ".join(lab_terms)]
    )
    return CvLabSimilarity(
        round(float(cosine_similarity(matrix[0], matrix[1])[0][0]) * 100),
        matched,
        cv_terms,
        lab_terms,
    )
