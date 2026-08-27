"""Build evaluation profiles from held-out reviews."""

from __future__ import annotations

from typing import Any, Literal

import pandas as pd

from engine.types import BeautyProfile
from src.config import CONCERN_REVIEW_VOCAB, EVAL_DEFAULT_BUDGET_USD, SKIN_TYPES

ProfileVariant = Literal["clean", "text_derived"]


def extract_concerns_from_text(text: str) -> tuple[str, ...]:
    lowered = text.lower()
    found: list[str] = []
    for concern, vocabulary in CONCERN_REVIEW_VOCAB.items():
        if any(term in lowered for term in vocabulary):
            found.append(concern)
    return tuple(found)


def build_profile_from_review(
    *,
    skin_type: str,
    secondary_category: str,
    review_text: str,
    variant: ProfileVariant,
    category_restricted: bool,
    budget_max_usd: float = EVAL_DEFAULT_BUDGET_USD,
) -> BeautyProfile:
    concerns: tuple[str, ...] = ()
    if variant == "text_derived":
        concerns = extract_concerns_from_text(review_text)

    return BeautyProfile(
        skin_type=skin_type,
        concerns=concerns,
        budget_max_usd=budget_max_usd,
        category=secondary_category if category_restricted else None,
    )


def build_profiles_for_review_row(
    row: pd.Series,
    product: dict[str, Any],
    *,
    category_restricted: bool,
    budget_max_usd: float = EVAL_DEFAULT_BUDGET_USD,
) -> dict[ProfileVariant, BeautyProfile]:
    skin_type = row.get("skin_type")
    if skin_type not in SKIN_TYPES:
        raise ValueError("review row missing valid skin_type")

    secondary_category = str(product.get("secondary_category") or "")
    review_text = str(row.get("review_text") or "")

    return {
        "clean": build_profile_from_review(
            skin_type=str(skin_type),
            secondary_category=secondary_category,
            review_text=review_text,
            variant="clean",
            category_restricted=category_restricted,
            budget_max_usd=budget_max_usd,
        ),
        "text_derived": build_profile_from_review(
            skin_type=str(skin_type),
            secondary_category=secondary_category,
            review_text=review_text,
            variant="text_derived",
            category_restricted=category_restricted,
            budget_max_usd=budget_max_usd,
        ),
    }
