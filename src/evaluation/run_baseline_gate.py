"""Phase 6 gate: baseline comparison, correlation, and weight tuning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.types import ContentWeights
from src.config import REPORTS_DIR, W_CONCERN, W_SKIN, W_TEXT
from src.evaluation.correlation import compute_component_correlation
from src.evaluation.evaluate import run_evaluation
from src.evaluation.tune_weights import tune_content_weights


def run_baseline_gate(
    *,
    split_name: str = "val",
    max_queries: int | None = 800,
    seed: int = 42,
    reports_dir: Path | None = None,
    skip_tuning: bool = False,
) -> dict[str, Any]:
    reports_dir = reports_dir or REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)
    correlation = compute_component_correlation(
        split_name=split_name,
        max_queries=max_queries,
        profile_variant="text_derived",
        candidate_variant="unrestricted",
    )

    default_weights = ContentWeights(w_skin=W_SKIN, w_concern=W_CONCERN, w_text=W_TEXT).normalized()
    baseline_eval = run_evaluation(
        split_name=split_name,
        max_queries=max_queries,
        seed=seed,
        content_weights=default_weights,
        output_path=reports_dir / f"baseline_{split_name}.json",
    )

    if skip_tuning:
        tuning = {
            "default_weights": {
                "w_skin": default_weights.w_skin,
                "w_concern": default_weights.w_concern,
                "w_text": default_weights.w_text,
            },
            "best_weights": {
                "w_skin": default_weights.w_skin,
                "w_concern": default_weights.w_concern,
                "w_text": default_weights.w_text,
            },
            "report_path": str(reports_dir / "weight_tuning.json"),
        }
        tuned_eval = baseline_eval
    else:
        tuning = tune_content_weights(
            split_name=split_name,
            max_queries=max_queries,
            seed=seed,
            output_path=reports_dir / "weight_tuning.json",
        )
        best_weights = ContentWeights(**tuning["best_weights"])

        tuned_eval = run_evaluation(
            split_name=split_name,
            max_queries=max_queries,
            seed=seed,
            content_weights=best_weights,
            rankers=("content",),
            output_path=reports_dir / f"baseline_{split_name}_tuned.json",
        )

    unrestricted = baseline_eval["variants"]["clean__unrestricted"]
    content = unrestricted["content"]
    popularity = unrestricted["popularity"]
    tuned = tuned_eval["variants"]["clean__unrestricted"]["content"]

    beats_popularity = content["hit_rate@10"] > popularity["hit_rate@10"]
    tuned_beats_popularity = tuned["hit_rate@10"] > popularity["hit_rate@10"]

    payload = {
        "split": split_name,
        "queries": baseline_eval["queries"],
        "correlation": correlation,
        "default_weights": tuning["default_weights"],
        "best_weights": tuning["best_weights"],
        "baseline_comparison": {
            "clean__unrestricted": {
                "content": {
                    "hit_rate@10": content["hit_rate@10"],
                    "mrr": content["mrr"],
                    "relevant_only": content["relevant_only"],
                },
                "popularity": {
                    "hit_rate@10": popularity["hit_rate@10"],
                    "mrr": popularity["mrr"],
                },
                "random": {
                    "hit_rate@10": unrestricted["random"]["hit_rate@10"],
                },
                "rating": {
                    "hit_rate@10": unrestricted["rating"]["hit_rate@10"],
                },
            },
            "clean__category_restricted": {
                "content_hit_rate@10": baseline_eval["variants"]["clean__category_restricted"][
                    "content"
                ]["hit_rate@10"],
                "popularity_hit_rate@10": baseline_eval["variants"]["clean__category_restricted"][
                    "popularity"
                ]["hit_rate@10"],
            },
        },
        "tuned_content_unrestricted": {
            "hit_rate@10": tuned["hit_rate@10"],
            "mrr": tuned["mrr"],
        },
        "gate": {
            "content_beats_popularity_unrestricted": beats_popularity,
            "tuned_content_beats_popularity_unrestricted": tuned_beats_popularity,
            "pass": beats_popularity or tuned_beats_popularity,
            "note": (
                "Gate uses unrestricted clean profile on validation split only. "
                "Test split remains untouched."
            ),
        },
        "reports": {
            "baseline": baseline_eval["report_path"],
            "tuning": tuning["report_path"],
            "tuned": tuned_eval["report_path"],
        },
    }

    output_path = reports_dir / "baseline_gate.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["report_path"] = str(output_path)
    return payload


def main() -> None:
    result = run_baseline_gate()
    print(json.dumps(result["gate"], indent=2))
    print(f"Wrote {result['report_path']}")


if __name__ == "__main__":
    main()
