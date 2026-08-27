"""Pydantic request/response models for the recommendation API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from src.config import CONCERNS, EXCLUSION_RULES, SKIN_TYPES

SkinType = Literal["combination", "dry", "normal", "oily"]
Concern = Literal[
    "hydration",
    "acne_oil_control",
    "brightening",
    "barrier_support",
    "anti_aging",
]
Exclusion = Literal["fragrance", "drying_alcohol", "paraben", "sulfate"]


class RecommendRequest(BaseModel):
    skin_type: SkinType
    concerns: list[Concern] = Field(default_factory=list)
    exclusions: list[Exclusion] = Field(default_factory=list)
    budget_max_usd: float = Field(default=9999.0, gt=0, le=9999.0)
    category: str | None = Field(default=None, min_length=1, max_length=120)
    top_k: int = Field(default=10, ge=1, le=50)

    @field_validator("concerns")
    @classmethod
    def dedupe_concerns(cls, value: list[Concern]) -> list[Concern]:
        seen: set[str] = set()
        unique: list[Concern] = []
        for concern in value:
            if concern not in seen:
                seen.add(concern)
                unique.append(concern)
        return unique

    @field_validator("exclusions")
    @classmethod
    def dedupe_exclusions(cls, value: list[Exclusion]) -> list[Exclusion]:
        seen: set[str] = set()
        unique: list[Exclusion] = []
        for exclusion in value:
            if exclusion not in seen:
                seen.add(exclusion)
                unique.append(exclusion)
        return unique

    @field_validator("category")
    @classmethod
    def strip_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ScoreBreakdownResponse(BaseModel):
    skin_match: float
    concern_match: float
    text_similarity: float
    content_score: float
    cohort_score: float
    quality_score: float
    final_score: float
    cohort_used: bool


class ExplanationReasonResponse(BaseModel):
    claim_id: str
    message: str
    evidence: list[str]


class ScoreComponentResponse(BaseModel):
    key: str
    label: str
    raw_score: float
    weight: float
    contribution: float


class ExplanationResponse(BaseModel):
    final_score: float
    cohort_used: bool
    reasons: list[ExplanationReasonResponse]
    components: list[ScoreComponentResponse]


class RecommendedProductResponse(BaseModel):
    product_id: str
    product_name: str
    brand: str
    price_usd: float
    rating: float | None
    review_count: int
    secondary_category: str
    tertiary_category: str
    derived_concerns: list[str]
    derived_benefits: list[str]
    suited_skin_types: list[str]
    scores: ScoreBreakdownResponse
    explanation: ExplanationResponse | None = None


class RecommendResponse(BaseModel):
    status: Literal["ok", "no_match"]
    profile: dict[str, object]
    items: list[RecommendedProductResponse]
    candidate_count: int
    filtered_count: int
    relaxations: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: str
    detail: str | list[object]
    received_path: str | None = None


def supported_values() -> dict[str, tuple[str, ...]]:
    return {
        "skin_types": SKIN_TYPES,
        "concerns": CONCERNS,
        "exclusions": tuple(EXCLUSION_RULES.keys()),
    }
