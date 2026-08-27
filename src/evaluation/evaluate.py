"""Run the full offline evaluation protocol."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pandas as pd

from engine.artifacts import ArtifactBundle, load_artifacts
from engine.types import ContentWeights, RankingConfig
from src.config import DATA_INTERIM, EVAL_TOP_K, REPORTS_DIR
from src.evaluation.metrics import (
    build_popularity_distribution,
    catalog_coverage,
    intra_list_diversity,
    novelty_at_k,
)
from src.evaluation.profiles import ProfileVariant
from src.evaluation.protocol import (
    CandidateVariant,
    EvalInstance,
    RankerName,
    aggregate_metrics,
    build_eval_instances,
    evaluate_instance,
)
from src.evaluation.split import temporal_split, verify_no_temporal_overlap

__all__ = [
    "CandidateVariant",
    "ProfileVariant",
    "RankerName",
    "run_evaluation",
]


def _catalog_by_id(catalog: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["product_id"]): item for item in catalog}


def _product_tags(catalog: list[dict[str, Any]]) -> dict[str, set[str]]:
    return {str(item["product_id"]): set(item.get("derived_concerns") or []) for item in catalog}


def _sample_instances(
    instances: list[EvalInstance],
    max_queries: int | None,
    seed: int,
) -> list[EvalInstance]:
    if max_queries is None or len(instances) <= max_queries:
        return instances
    rng = random.Random(seed)
    return rng.sample(instances, max_queries)


def run_evaluation(
    *,
    artifacts: ArtifactBundle | None = None,
    split_name: str = "val",
    max_queries: int | None = None,
    seed: int = 42,
    output_path: Path | None = None,
    content_weights: ContentWeights | None = None,
    ranking_config: RankingConfig | None = None,
    text_similarity_fn: Any | None = None,
    rankers: tuple[RankerName, ...] = ("content", "random", "popularity", "rating"),
    profile_variants: tuple[ProfileVariant, ...] = ("clean", "text_derived"),
    candidate_variants: tuple[CandidateVariant, ...] = (
        "category_restricted",
        "unrestricted",
    ),
) -> dict[str, Any]:
    artifacts = artifacts or load_artifacts()
    reviews_path = DATA_INTERIM / "reviews_clean.parquet"
    if not reviews_path.exists():
        raise FileNotFoundError("cleaned reviews not found; run preprocessing first")

    reviews = temporal_split(pd.read_parquet(reviews_path))
    if not verify_no_temporal_overlap(reviews):
        raise RuntimeError("temporal split overlap detected")

    catalog_by_id = _catalog_by_id(artifacts.catalog)
    instances = build_eval_instances(reviews, catalog_by_id, split=split_name)
    instances = _sample_instances(instances, max_queries, seed)

    results: dict[str, Any] = {
        "split": split_name,
        "queries": len(instances),
        "temporal_overlap": False,
        "variants": {},
    }

    popularity_prob = build_popularity_distribution(artifacts.catalog)
    tags = _product_tags(artifacts.catalog)

    for profile_variant in profile_variants:
        for candidate_variant in candidate_variants:
            variant_key = f"{profile_variant}__{candidate_variant}"
            results["variants"][variant_key] = {}

            for ranker in rankers:
                rows: list[dict[str, Any]] = []
                recommendation_lists: list[list[str]] = []

                for offset, instance in enumerate(instances):
                    row = reviews.loc[instance.review_index]
                    product = catalog_by_id[instance.product_id]
                    row_result = evaluate_instance(
                        instance,
                        row,
                        product,
                        artifacts,
                        profile_variant=profile_variant,
                        candidate_variant=candidate_variant,
                        ranker=ranker,
                        k_values=EVAL_TOP_K,
                        seed=seed + offset,
                        content_weights=content_weights,
                        ranking_config=ranking_config,
                        text_similarity_fn=text_similarity_fn,
                    )
                    rows.append(row_result)
                    recommendation_lists.append(row_result["ranked_ids"][: max(EVAL_TOP_K)])

                aggregated: dict[str, Any] = aggregate_metrics(rows)
                aggregated["relevant_only"] = aggregate_metrics(rows, relevant_only=True)
                aggregated["coverage@10"] = catalog_coverage(
                    [recs[:10] for recs in recommendation_lists],
                    len(artifacts.catalog),
                )
                aggregated["diversity@10"] = sum(
                    intra_list_diversity(recs[:10], tags) for recs in recommendation_lists if recs
                ) / max(len(recommendation_lists), 1)
                aggregated["novelty@10"] = sum(
                    novelty_at_k(recs, popularity_prob, 10) for recs in recommendation_lists if recs
                ) / max(len(recommendation_lists), 1)
                results["variants"][variant_key][ranker] = aggregated

    split_counts = reviews["split"].value_counts().to_dict()
    results["split_counts"] = {str(key): int(value) for key, value in split_counts.items()}

    output_path = output_path or (REPORTS_DIR / f"evaluation_{split_name}.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    results["report_path"] = str(output_path)
    return results


def main() -> None:
    result = run_evaluation(split_name="val", max_queries=200)
    print(json.dumps({key: result[key] for key in ("split", "queries", "report_path")}, indent=2))


if __name__ == "__main__":
    main()
