"""Shared helpers for data preparation."""

from __future__ import annotations

import ast
import json
import re
import warnings
from typing import Any

import pandas as pd

WHITESPACE_RE = re.compile(r"\s+")


def normalize_id(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def collapse_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def parse_stringified_list(raw: object) -> list[str]:
    """Parse a CSV cell that stores a Python list literal."""
    if pd.isna(raw):
        return []

    text = str(raw).strip()
    if not text:
        return []

    # Ingredient cells often embed Water\Aqua\Eau. Those backslashes are not
    # Python escapes; doubling them keeps literal_eval quiet on 3.12+ and
    # preserves a stable token string for keyword matching.
    sanitized = text.replace("\\", "\\\\")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            parsed = ast.literal_eval(sanitized)
    except (SyntaxError, ValueError):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return []

    if not isinstance(parsed, list):
        return []

    items: list[str] = []
    for item in parsed:
        if item is None:
            continue
        cleaned = collapse_whitespace(str(item).replace("\\", "/"))
        if cleaned:
            items.append(cleaned)
    return items


def parse_ingredient_tokens(raw: object) -> list[str]:
    """Turn a stringified ingredient list into normalized ingredient tokens."""
    chunks = parse_stringified_list(raw)
    if not chunks:
        return []

    combined = ", ".join(chunks)
    tokens: list[str] = []
    seen: set[str] = set()

    for part in combined.split(","):
        token = collapse_whitespace(part)
        if not token:
            continue
        # Skip variant labels like "Capri Eau de Parfum:" with no ingredients.
        if token.endswith(":") and len(token.split()) <= 6:
            continue
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        tokens.append(token)

    return tokens


def parse_highlights(raw: object) -> list[str]:
    items = parse_stringified_list(raw)
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        # Fix common spacing artifacts such as "&Spicy".
        cleaned = item.replace("&", " & ").replace("  ", " ")
        cleaned = collapse_whitespace(cleaned)
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    return normalized


def drop_report(
    reason: str,
    count: int,
    reports: dict[str, int],
) -> None:
    reports[reason] = reports.get(reason, 0) + count


def merge_reports(*reports: dict[str, int]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for report in reports:
        for key, value in report.items():
            merged[key] = merged.get(key, 0) + value
    return merged


def save_reconciliation(path: Any, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
