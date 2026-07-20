from __future__ import annotations

import re
from abc import ABC, abstractmethod


def tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[\w가-힣]+", value.lower()) if len(token) > 1}


class SemanticSimilarityProvider(ABC):
    @abstractmethod
    def similarity(self, left: str, right: str) -> float: ...


class DeterministicLexicalSimilarityProvider(SemanticSimilarityProvider):
    """Jaccard similarity over Korean and English word tokens."""

    def similarity(self, left: str, right: str) -> float:
        left_tokens, right_tokens = tokens(left), tokens(right)
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
