"""Measure pairwise correlation between content-score components."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from engine.artifacts import ArtifactBundle, load_artifacts
from engine.constraints import filter_catalog
from engine.content_ranker import build_profile_text, score_content_components
from src.config import DATA_INTERIM
from src.evaluation.protocol import build_eval_instances, profile_for_instance
from src.evaluation.split import temporal_split


def compute_component_correlation(
    *,
    artifacts: ArtifactBundle | None = None,
    split_name: str = "val",
    max_queries: int | None = 500,
    profile_variant: str = "text_derived",
    candidate_variant: str = "category_restricted",
) -> dict[str, Any]:
    artifacts = artifacts or load_artifacts()
    reviews = temporal_split(pd.read_parquet(DATA_INTERIM / "reviews_clean.parquet"))
    catalog_by_id = {item["product_id"]: item for item in artifacts.catalog}
    instances = build_eval_instances(reviews, catalog_by_id, split=split_name)
    if max_queries is not None:
        instances = instances[:max_queries]

    skin_values: list[float] = []
    concern_values: list[float] = []
    text_values: list[float] = []

    for instance in instances:
        row = reviews.loc[instance.review_index]
        product = catalog_by_id[instance.product_id]
        profile = profile_for_instance(
            row,
            product,
            profile_variant=profile_variant,  # type: ignore[arg-type]
            candidate_variant=candidate_variant,  # type: ignore[arg-type]
        )
        eligible_indices, _ = filter_catalog(artifacts.catalog, profile)
        if not eligible_indices:
            continue

        eligible_products = [artifacts.catalog[index] for index in eligible_indices]
        profile_vector = artifacts.tfidf_model.transform(build_profile_text(profile))
        text_similarities = artifacts.text_similarities(profile_vector)[np.array(eligible_indices)]
        skin, concern, text, _ = score_content_components(
            eligible_products,
            profile,
            text_similarities,
        )
        skin_values.extend(skin.tolist())
        concern_values.extend(concern.tolist())
        text_values.extend(text.tolist())

    matrix_raw = np.corrcoef(
        np.array([skin_values, concern_values, text_values], dtype=np.float64),
    )
    matrix = np.atleast_2d(np.nan_to_num(matrix_raw, nan=0.0))
    labels = ("skin_match", "concern_match", "text_similarity")
    pairs = {
        f"{labels[i]}__{labels[j]}": float(matrix[i, j])
        for i in range(len(labels))
        for j in range(i + 1, len(labels))
    }

    return {
        "split": split_name,
        "profile_variant": profile_variant,
        "candidate_variant": candidate_variant,
        "observations": len(skin_values),
        "labels": list(labels),
        "matrix": matrix.tolist(),
        "pairs": pairs,
    }
