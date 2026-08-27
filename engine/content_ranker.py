"""Content-based scoring over skin, concern, and text similarity."""

from __future__ import annotations

from typing import Any

import numpy as np

from engine.types import BeautyProfile, ContentWeights
from src.config import CONCERN_REVIEW_VOCAB, SKIN_MATCH_NEUTRAL, W_CONCERN, W_SKIN, W_TEXT


def default_content_weights() -> ContentWeights:
    return ContentWeights(w_skin=W_SKIN, w_concern=W_CONCERN, w_text=W_TEXT).normalized()


def build_profile_text(profile: BeautyProfile) -> str:
    parts = [profile.skin_type, f"{profile.skin_type} skin"]
    for concern in profile.concerns:
        parts.extend(CONCERN_REVIEW_VOCAB.get(concern, (concern.replace("_", " "),)))
    return " ".join(parts)


def skin_match_score(product: dict[str, Any], profile: BeautyProfile) -> float:
    suited = product.get("suited_skin_types") or []
    if not suited:
        return SKIN_MATCH_NEUTRAL
    if profile.skin_type in suited:
        return 1.0
    return 0.0


def concern_match_score(product: dict[str, Any], profile: BeautyProfile) -> float:
    if not profile.concerns:
        return 1.0

    product_concerns = set(product.get("derived_concerns") or [])
    user_concerns = set(profile.concerns)
    overlap = product_concerns & user_concerns
    return len(overlap) / len(user_concerns)


def content_score(
    skin: float,
    concern: float,
    text: float,
    weights: ContentWeights | None = None,
) -> float:
    resolved = weights or default_content_weights()
    return resolved.w_skin * skin + resolved.w_concern * concern + resolved.w_text * text


def score_content_components(
    products: list[dict[str, Any]],
    profile: BeautyProfile,
    text_similarities: np.ndarray,
    weights: ContentWeights | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    resolved = weights or default_content_weights()
    skin_scores = np.array(
        [skin_match_score(product, profile) for product in products],
        dtype=np.float32,
    )
    concern_scores = np.array(
        [concern_match_score(product, profile) for product in products],
        dtype=np.float32,
    )
    text_scores = np.clip(text_similarities, 0.0, 1.0).astype(np.float32)
    totals = (
        resolved.w_skin * skin_scores
        + resolved.w_concern * concern_scores
        + resolved.w_text * text_scores
    ).astype(np.float32)
    return skin_scores, concern_scores, text_scores, totals
