"""Grid-search content weights on the validation split."""

from __future__ import annotations

import json
from itertools import product
from pathlib import Path
from typing import Any

from engine.types import ContentWeights
from src.config import REPORTS_DIR, W_CONCERN, W_SKIN, W_TEXT
from src.evaluation.evaluate import run_evaluation


def _weight_grid(step: float = 0.17) -> list[ContentWeights]:
    values = [round(step * index, 4) for index in range(1, int(1 / step))]
    candidates: list[ContentWeights] = []
    for w_skin, w_concern in product(values, values):
        w_text = round(1.0 - w_skin - w_concern, 4)
        if w_text <= 0.05:
            continue
        candidates.append(ContentWeights(w_skin=w_skin, w_concern=w_concern, w_text=w_text))
    return candidates


def tune_content_weights(
    *,
    split_name: str = "val",
    max_queries: int | None = 800,
    seed: int = 42,
    output_path: Path | None = None,
) -> dict[str, Any]:
    grid = _weight_grid()
    baseline = ContentWeights(w_skin=W_SKIN, w_concern=W_CONCERN, w_text=W_TEXT).normalized()
    grid.append(baseline)

    rows: list[dict[str, Any]] = []
    for weights in grid:
        result = run_evaluation(
            split_name=split_name,
            max_queries=max_queries,
            seed=seed,
            content_weights=weights,
            rankers=("content",),
            profile_variants=("clean",),
            candidate_variants=("unrestricted",),
            output_path=None,
        )
        unrestricted = result["variants"]["clean__unrestricted"]["content"]
        relevant = unrestricted["relevant_only"]
        rows.append(
            {
                "weights": {
                    "w_skin": weights.w_skin,
                    "w_concern": weights.w_concern,
                    "w_text": weights.w_text,
                },
                "hit_rate@10": unrestricted["hit_rate@10"],
                "mrr": unrestricted["mrr"],
                "ndcg@10": unrestricted["ndcg@10"],
                "relevant_hit_rate@10": relevant.get("hit_rate@10", 0.0),
                "relevant_mrr": relevant.get("mrr", 0.0),
            }
        )

    rows.sort(key=lambda row: (row["hit_rate@10"], row["mrr"]), reverse=True)
    best = rows[0]

    payload = {
        "split": split_name,
        "queries": max_queries,
        "grid_size": len(grid),
        "default_weights": {
            "w_skin": baseline.w_skin,
            "w_concern": baseline.w_concern,
            "w_text": baseline.w_text,
        },
        "best_weights": best["weights"],
        "best_metrics": {
            "hit_rate@10": best["hit_rate@10"],
            "mrr": best["mrr"],
            "ndcg@10": best["ndcg@10"],
            "relevant_hit_rate@10": best["relevant_hit_rate@10"],
        },
        "top_configs": rows[:5],
    }

    output_path = output_path or (REPORTS_DIR / "weight_tuning.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["report_path"] = str(output_path)
    return payload
