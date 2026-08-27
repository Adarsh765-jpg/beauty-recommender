"""Evaluation protocol: held-out review instances and ranking runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd

from engine.artifacts import ArtifactBundle
from engine.ranking import rank_product_ids
from engine.types import BeautyProfile, ContentWeights, RankingConfig
from src.evaluation.baselines import rank_popularity, rank_random, rank_rating
from src.evaluation.metrics import compute_accuracy_metrics
from src.evaluation.profiles import ProfileVariant, build_profiles_for_review_row
from src.evaluation.relevance import is_relevant

CandidateVariant = Literal["category_restricted", "unrestricted"]
RankerName = Literal["content", "random", "popularity", "rating"]


@dataclass(frozen=True)
class EvalInstance:
    review_index: int
    product_id: str
    split: str
    relevant: bool
    skin_type: str
    secondary_category: str


def build_eval_instances(
    reviews: pd.DataFrame,
    catalog_by_id: dict[str, dict[str, Any]],
    *,
    split: str | None = None,
) -> list[EvalInstance]:
    instances: list[EvalInstance] = []
    for index, row in reviews.iterrows():
        if split is not None and row.get("split") != split:
            continue
        if not row.get("has_valid_skin_type", False):
            continue

        product_id = str(row["product_id"])
        product = catalog_by_id.get(product_id)
        if product is None:
            continue
        if product.get("out_of_stock"):
            continue

        instances.append(
            EvalInstance(
                review_index=int(index),
                product_id=product_id,
                split=str(row.get("split", "unknown")),
                relevant=is_relevant(row.get("is_recommended"), int(row["rating"])),
                skin_type=str(row["skin_type"]),
                secondary_category=str(product.get("secondary_category") or ""),
            )
        )
    return instances


def profile_for_instance(
    row: pd.Series,
    product: dict[str, Any],
    *,
    profile_variant: ProfileVariant,
    candidate_variant: CandidateVariant,
) -> BeautyProfile:
    profiles = build_profiles_for_review_row(
        row,
        product,
        category_restricted=candidate_variant == "category_restricted",
    )
    return profiles[profile_variant]


def rank_for_eval(
    profile: BeautyProfile,
    artifacts: ArtifactBundle,
    ranker: RankerName,
    *,
    seed: int,
    content_weights: ContentWeights | None = None,
    ranking_config: RankingConfig | None = None,
    text_similarity_fn: Any | None = None,
) -> list[str]:
    if ranker == "content":
        return rank_product_ids(
            profile,
            artifacts,
            content_weights=content_weights,
            ranking_config=ranking_config,
            text_similarity_fn=text_similarity_fn,
        )
    if ranker == "random":
        return rank_random(profile, artifacts, seed=seed)
    if ranker == "popularity":
        return rank_popularity(profile, artifacts)
    if ranker == "rating":
        return rank_rating(profile, artifacts)
    raise ValueError(f"unknown ranker: {ranker}")


def evaluate_instance(
    instance: EvalInstance,
    row: pd.Series,
    product: dict[str, Any],
    artifacts: ArtifactBundle,
    *,
    profile_variant: ProfileVariant,
    candidate_variant: CandidateVariant,
    ranker: RankerName,
    k_values: tuple[int, ...],
    seed: int,
    content_weights: ContentWeights | None = None,
    ranking_config: RankingConfig | None = None,
    text_similarity_fn: Any | None = None,
) -> dict[str, Any]:
    profile = profile_for_instance(
        row,
        product,
        profile_variant=profile_variant,
        candidate_variant=candidate_variant,
    )
    ranked_ids = rank_for_eval(
        profile,
        artifacts,
        ranker,
        seed=seed,
        content_weights=content_weights,
        ranking_config=ranking_config,
        text_similarity_fn=text_similarity_fn,
    )
    relevant_ids = {instance.product_id} if instance.relevant else set()

    metrics = compute_accuracy_metrics(ranked_ids, relevant_ids, k_values)
    if instance.product_id in ranked_ids:
        target_rank = ranked_ids.index(instance.product_id) + 1
    else:
        target_rank = None

    return {
        "review_index": instance.review_index,
        "product_id": instance.product_id,
        "relevant": instance.relevant,
        "candidate_count": len(ranked_ids),
        "target_rank": target_rank,
        "ranked_ids": ranked_ids,
        "metrics": metrics,
    }


def aggregate_metrics(
    rows: list[dict[str, Any]],
    *,
    relevant_only: bool = False,
) -> dict[str, float]:
    subset = [row for row in rows if row["relevant"]] if relevant_only else rows
    if not subset:
        return {"queries": 0.0}

    metric_names = subset[0]["metrics"].keys()
    aggregated: dict[str, float] = {}
    for name in metric_names:
        aggregated[name] = sum(row["metrics"][name] for row in subset) / len(subset)
    aggregated["queries"] = float(len(subset))
    aggregated["avg_candidate_count"] = sum(row["candidate_count"] for row in subset) / len(subset)
    if relevant_only:
        aggregated["relevant_only"] = 1.0
    return aggregated
