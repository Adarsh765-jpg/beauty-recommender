"""Shared final-score computation for ranking and explanations."""

from __future__ import annotations

from engine.types import RankingConfig, ScoreBreakdown


def compute_final_score(
    breakdown: ScoreBreakdown,
    config: RankingConfig,
) -> float:
    flags = config.flags
    weights = config.mixing

    content_value = breakdown.content_score if flags.use_content else 0.0
    quality_value = breakdown.quality_score if flags.use_quality else 0.0
    use_cohort_term = flags.use_cohort and breakdown.cohort_used
    cohort_value = breakdown.cohort_score if use_cohort_term else 0.0

    if use_cohort_term:
        return (
            weights.alpha * content_value
            + weights.beta * cohort_value
            + weights.gamma * quality_value
        )
    return weights.alpha * content_value + weights.gamma * quality_value
