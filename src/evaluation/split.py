"""Temporal train/validation/test split on review submission time."""

from __future__ import annotations

from typing import Literal, cast

import pandas as pd

from src.config import EVAL_TRAIN_RATIO, EVAL_VAL_RATIO

SplitName = Literal["train", "val", "test"]


def temporal_split(reviews: pd.DataFrame) -> pd.DataFrame:
    """Assign each review to train, val, or test by ``submission_time``."""
    if "submission_time" not in reviews.columns:
        raise ValueError("reviews must include submission_time")

    ordered = reviews.sort_values("submission_time").reset_index(drop=True)
    row_count = len(ordered)
    train_end = int(row_count * EVAL_TRAIN_RATIO)
    val_end = train_end + int(row_count * EVAL_VAL_RATIO)

    splits: list[SplitName] = cast(
        "list[SplitName]",
        ["train"] * train_end + ["val"] * (val_end - train_end),
    )
    splits.extend(cast("list[SplitName]", ["test"] * (row_count - len(splits))))

    result = ordered.copy()
    result["split"] = splits
    return result


def split_bounds(reviews: pd.DataFrame) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    """Return inclusive time bounds per split for leakage checks."""
    if "split" not in reviews.columns:
        reviews = temporal_split(reviews)

    bounds: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {}
    for name in ("train", "val", "test"):
        subset = reviews.loc[reviews["split"] == name, "submission_time"]
        if subset.empty:
            continue
        bounds[name] = (subset.min(), subset.max())
    return bounds


def verify_no_temporal_overlap(reviews: pd.DataFrame) -> bool:
    """Verify splits are disjoint and ordered by sorted submission time."""
    bounds = split_bounds(reviews)
    if not {"train", "val", "test"}.issubset(bounds):
        return False

    train_rows = reviews.loc[reviews["split"] == "train"]
    val_rows = reviews.loc[reviews["split"] == "val"]
    test_rows = reviews.loc[reviews["split"] == "test"]
    if train_rows.empty or val_rows.empty or test_rows.empty:
        return False

    # Index-based split guarantees disjoint rows even when timestamps tie.
    train_max_index = int(train_rows.index.max())
    val_min_index = int(val_rows.index.min())
    val_max_index = int(val_rows.index.max())
    test_min_index = int(test_rows.index.min())
    if not (train_max_index < val_min_index and val_max_index < test_min_index):
        return False

    # Every train row must be at or before every val/test row in submission time.
    train_max_time = train_rows["submission_time"].max()
    val_min_time = val_rows["submission_time"].min()
    test_min_time = test_rows["submission_time"].min()
    val_max_time = val_rows["submission_time"].max()
    return bool(train_max_time <= val_min_time and val_max_time <= test_min_time)
