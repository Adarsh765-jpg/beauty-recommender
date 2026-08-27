"""Shared tokenizer used offline (scikit-learn) and online (numpy runtime)."""

from __future__ import annotations

import re

TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")

STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "for",
        "in",
        "of",
        "the",
        "to",
        "with",
    }
)


def tokenize(text: str) -> list[str]:
    """Tokenize product or profile text for TF-IDF."""
    if not text:
        return []

    lowered = text.lower()
    tokens = TOKEN_PATTERN.findall(lowered)
    return [token for token in tokens if len(token) > 1 and token not in STOPWORDS]
