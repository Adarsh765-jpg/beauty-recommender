"""Derive skin-type suitability from product highlights."""

from __future__ import annotations

import re

from src.config import SKIN_TYPES

SKIN_ALIASES = {
    "dry": "dry",
    "oily": "oily",
    "combo": "combination",
    "combination": "combination",
    "normal": "normal",
}

BEST_FOR_PATTERN = re.compile(
    r"best for\s+(?P<types>[a-z,\s]+)",
    re.IGNORECASE,
)

NEGATION_PREFIX = re.compile(r"\b(not|no|without|avoid|unsuitable)\b", re.IGNORECASE)


def _parse_skin_tokens(fragment: str) -> set[str]:
    suited: set[str] = set()
    for raw in re.split(r"[,/]", fragment):
        token = raw.strip().lower()
        if not token:
            continue
        if token in SKIN_ALIASES:
            suited.add(SKIN_ALIASES[token])
        elif token.endswith(" skin"):
            key = token.replace(" skin", "").strip()
            if key in SKIN_ALIASES:
                suited.add(SKIN_ALIASES[key])
    return suited


def _is_negated(context: str, match_start: int) -> bool:
    prefix = context[max(0, match_start - 40) : match_start].lower()
    return bool(NEGATION_PREFIX.search(prefix))


def _positive_for_skin(blob: str, aliases: tuple[str, ...]) -> bool:
    for alias in aliases:
        pattern = re.compile(rf"\bfor\s+{re.escape(alias)}\b", re.IGNORECASE)
        for match in pattern.finditer(blob):
            if not _is_negated(blob, match.start()):
                return True
    return False


def derive_suited_skin_types(highlights: list[str]) -> list[str]:
    suited: set[str] = set()
    blob = " ".join(highlights).lower()

    for highlight in highlights:
        match = BEST_FOR_PATTERN.search(highlight)
        if match and not _is_negated(highlight, match.start()):
            suited |= _parse_skin_tokens(match.group("types"))

        lower = highlight.lower()
        if lower.startswith("best for dry skin"):
            suited.add("dry")
        if lower.startswith("best for oily skin"):
            suited.add("oily")
        if lower.startswith("best for combination skin"):
            suited.add("combination")
        if lower.startswith("best for normal skin"):
            suited.add("normal")

    if _positive_for_skin(blob, ("dry",)) and "dryness" not in blob:
        suited.add("dry")
    if _positive_for_skin(blob, ("oily",)):
        suited.add("oily")

    return sorted(s for s in suited if s in SKIN_TYPES)
