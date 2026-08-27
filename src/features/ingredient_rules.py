"""Concern and exclusion rule helpers."""

from __future__ import annotations

from src.config import (
    EXCLUSION_RULES,
    HIGHLIGHT_CONCERN_RULES,
    INGREDIENT_CONCERN_RULES,
)


def _contains_pattern(text: str, pattern: str) -> bool:
    return pattern in text


def match_concerns_from_ingredients(ingredients: list[str]) -> set[str]:
    blob = " ".join(ingredients).lower()
    matched: set[str] = set()
    for pattern, concern in INGREDIENT_CONCERN_RULES:
        if _contains_pattern(blob, pattern):
            matched.add(concern)
    return matched


def match_concerns_from_highlights(highlights: list[str]) -> set[str]:
    blob = " ".join(highlights).lower()
    matched: set[str] = set()
    for pattern, concern in HIGHLIGHT_CONCERN_RULES:
        if _contains_pattern(blob, pattern):
            matched.add(concern)
    return matched


def derive_concerns(ingredients: list[str], highlights: list[str]) -> list[str]:
    concerns = match_concerns_from_ingredients(ingredients) | match_concerns_from_highlights(
        highlights
    )
    return sorted(concerns)


def detect_exclusions(ingredients: list[str]) -> dict[str, bool]:
    blob = " ".join(ingredients).lower()
    flags: dict[str, bool] = {}
    for name, patterns in EXCLUSION_RULES.items():
        flags[name] = any(pattern in blob for pattern in patterns)
    return flags
