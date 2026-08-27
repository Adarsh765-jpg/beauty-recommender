"""Shared request/response types for the runtime engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BeautyProfile:
    skin_type: str
    concerns: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()
    budget_max_usd: float = 9999.0
    category: str | None = None


@dataclass(frozen=True)
class ContentWeights:
    w_skin: float
    w_concern: float
    w_text: float

    def normalized(self) -> ContentWeights:
        total = self.w_skin + self.w_concern + self.w_text
        if total <= 0:
            raise ValueError("content weights must sum to a positive value")
        return ContentWeights(
            w_skin=self.w_skin / total,
            w_concern=self.w_concern / total,
            w_text=self.w_text / total,
        )


@dataclass(frozen=True)
class MixingWeights:
    alpha: float
    beta: float
    gamma: float


@dataclass(frozen=True)
class RankingFlags:
    use_content: bool = True
    use_cohort: bool = True
    use_quality: bool = True


@dataclass(frozen=True)
class RankingConfig:
    mixing: MixingWeights
    flags: RankingFlags = field(default_factory=RankingFlags)


@dataclass(frozen=True)
class ExplanationReason:
    claim_id: str
    message: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ScoreComponent:
    key: str
    label: str
    raw_score: float
    weight: float
    contribution: float


@dataclass(frozen=True)
class ProductExplanation:
    reasons: tuple[ExplanationReason, ...]
    components: tuple[ScoreComponent, ...]
    final_score: float
    cohort_used: bool


@dataclass(frozen=True)
class ScoreBreakdown:
    skin_match: float
    concern_match: float
    text_similarity: float
    content_score: float
    cohort_score: float
    quality_score: float
    final_score: float
    cohort_used: bool


@dataclass(frozen=True)
class RankedProduct:
    product_id: str
    product_name: str
    brand: str
    price_usd: float
    rating: float | None
    review_count: int
    secondary_category: str
    tertiary_category: str
    derived_concerns: tuple[str, ...]
    derived_benefits: tuple[str, ...]
    suited_skin_types: tuple[str, ...]
    breakdown: ScoreBreakdown
    explanation: ProductExplanation | None = None


@dataclass
class RankingResult:
    items: list[RankedProduct] = field(default_factory=list)
    candidate_count: int = 0
    filtered_count: int = 0
    relaxations: list[str] = field(default_factory=list)


def profile_to_dict(profile: BeautyProfile) -> dict[str, Any]:
    return {
        "skin_type": profile.skin_type,
        "concerns": list(profile.concerns),
        "exclusions": list(profile.exclusions),
        "budget_max_usd": profile.budget_max_usd,
        "category": profile.category,
    }
