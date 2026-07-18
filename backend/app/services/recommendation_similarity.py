from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod

from app.services.document_analysis.service import get_openai_client


def tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[\w가-힣]+", value.lower()) if len(token) > 1}


class SemanticSimilarityProvider(ABC):
    @abstractmethod
    def similarity(self, left: str, right: str) -> float: ...


class DeterministicLexicalSimilarityProvider(SemanticSimilarityProvider):
    """Stable fallback: Jaccard similarity over Korean/English word tokens."""

    def similarity(self, left: str, right: str) -> float:
        left_tokens, right_tokens = tokens(left), tokens(right)
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


class OpenAIEmbeddingSimilarityProvider(SemanticSimilarityProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.client = get_openai_client(api_key, timeout_seconds=30.0)
        self.model = model

    def similarity(self, left: str, right: str) -> float:
        response = self.client.embeddings.create(model=self.model, input=[left, right])
        first, second = (item.embedding for item in response.data)
        denominator = math.sqrt(sum(value * value for value in first)) * math.sqrt(
            sum(value * value for value in second)
        )
        return (
            0.0
            if denominator == 0
            else max(
                0.0,
                min(
                    1.0,
                    sum(a * b for a, b in zip(first, second, strict=True)) / denominator,
                ),
            )
        )
