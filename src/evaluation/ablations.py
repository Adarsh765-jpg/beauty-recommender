"""Phase 8 ablation study: disable content, cohort, or quality independently."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.types import MixingWeights, RankingConfig, RankingFlags
from src.config import ALPHA, BETA, GAMMA, REPORTS_DIR
from src.evaluation.evaluate import run_evaluation

ABLATION_VARIANTS: dict[str, RankingFlags] = {
    "full": RankingFlags(use_content=True, use_cohort=True, use_quality=True),
    "no_content": RankingFlags(use_content=False, use_cohort=True, use_quality=True),
    "no_cohort": RankingFlags(use_content=True, use_cohort=False, use_quality=True),
    "no_quality": RankingFlags(use_content=True, use_cohort=True, use_quality=False),
}

WEIGHT_SWEEP: tuple[tuple[float, float, float], ...] = (
    (0.60, 0.25, 0.15),
    (0.55, 0.30, 0.15),
    (0.65, 0.20, 0.15),
    (0.50, 0.35, 0.15),
    (0.70, 0.15, 0.15),
    (0.60, 0.15, 0.25),
    (0.60, 0.35, 0.05),
)


def _ranking_config_for_flags(flags: RankingFlags) -> RankingConfig:
    return RankingConfig(
        mixing=MixingWeights(alpha=ALPHA, beta=BETA, gamma=GAMMA),
        flags=flags,
    )


def _ranking_config_for_weights(alpha: float, beta: float, gamma: float) -> RankingConfig:
    return RankingConfig(
        mixing=MixingWeights(alpha=alpha, beta=beta, gamma=gamma),
        flags=RankingFlags(),
    )


def _variant_metrics(eval_result: dict[str, Any], variant_key: str) -> dict[str, float]:
    content = eval_result["variants"][variant_key]["content"]
    return {
        "hit_rate@10": content["hit_rate@10"],
        "mrr": content["mrr"],
        "hit_rate@5": content["hit_rate@5"],
        "queries": content["queries"],
    }


def run_ablation_study(
    *,
    split_name: str = "val",
    max_queries: int | None = 800,
    seed: int = 42,
    profile_variant: str = "clean",
    candidate_variant: str = "unrestricted",
    reports_dir: Path | None = None,
) -> dict[str, Any]:
    reports_dir = reports_dir or REPORTS_DIR
    variant_key = f"{profile_variant}__{candidate_variant}"
    results: dict[str, Any] = {}

    for name, flags in ABLATION_VARIANTS.items():
        eval_result = run_evaluation(
            split_name=split_name,
            max_queries=max_queries,
            seed=seed,
            rankers=("content",),
            profile_variants=(profile_variant,),  # type: ignore[arg-type]
            candidate_variants=(candidate_variant,),  # type: ignore[arg-type]
            ranking_config=_ranking_config_for_flags(flags),
            output_path=reports_dir / f"ablation_{name}_{split_name}.json",
        )
        results[name] = {
            "flags": {
                "use_content": flags.use_content,
                "use_cohort": flags.use_cohort,
                "use_quality": flags.use_quality,
            },
            "metrics": _variant_metrics(eval_result, variant_key),
            "report_path": eval_result["report_path"],
        }

    full = results["full"]["metrics"]
    no_cohort = results["no_cohort"]["metrics"]
    no_quality = results["no_quality"]["metrics"]
    no_content = results["no_content"]["metrics"]

    payload = {
        "split": split_name,
        "variant_key": variant_key,
        "queries": full["queries"],
        "ablations": results,
        "comparison": {
            "full_vs_no_cohort": {
                "delta_hit_rate@10": full["hit_rate@10"] - no_cohort["hit_rate@10"],
                "delta_mrr": full["mrr"] - no_cohort["mrr"],
            },
            "full_vs_no_quality": {
                "delta_hit_rate@10": full["hit_rate@10"] - no_quality["hit_rate@10"],
                "delta_mrr": full["mrr"] - no_quality["mrr"],
            },
            "full_vs_no_content": {
                "delta_hit_rate@10": full["hit_rate@10"] - no_content["hit_rate@10"],
                "delta_mrr": full["mrr"] - no_content["mrr"],
            },
        },
    }

    output_path = reports_dir / f"ablation_study_{split_name}.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["report_path"] = str(output_path)
    return payload


def run_weight_sweep(
    *,
    split_name: str = "val",
    max_queries: int | None = 800,
    seed: int = 42,
    profile_variant: str = "clean",
    candidate_variant: str = "unrestricted",
    reports_dir: Path | None = None,
) -> dict[str, Any]:
    reports_dir = reports_dir or REPORTS_DIR
    variant_key = f"{profile_variant}__{candidate_variant}"
    rows: list[dict[str, Any]] = []
    query_count = 0.0

    for alpha, beta, gamma in WEIGHT_SWEEP:
        config = _ranking_config_for_weights(alpha, beta, gamma)
        eval_result = run_evaluation(
            split_name=split_name,
            max_queries=max_queries,
            seed=seed,
            rankers=("content",),
            profile_variants=(profile_variant,),  # type: ignore[arg-type]
            candidate_variants=(candidate_variant,),  # type: ignore[arg-type]
            ranking_config=config,
        )
        metrics = _variant_metrics(eval_result, variant_key)
        query_count = metrics["queries"]
        rows.append(
            {
                "alpha": alpha,
                "beta": beta,
                "gamma": gamma,
                "hit_rate@10": metrics["hit_rate@10"],
                "mrr": metrics["mrr"],
            }
        )

    best = max(rows, key=lambda row: (row["hit_rate@10"], row["mrr"]))
    current = next(row for row in rows if row["alpha"] == ALPHA and row["beta"] == BETA)

    payload = {
        "split": split_name,
        "variant_key": variant_key,
        "queries": query_count,
        "grid": rows,
        "current_weights": {"alpha": ALPHA, "beta": BETA, "gamma": GAMMA},
        "current_metrics": {
            "hit_rate@10": current["hit_rate@10"],
            "mrr": current["mrr"],
        },
        "best_on_grid": best,
        "current_is_best": (
            best["alpha"] == ALPHA and best["beta"] == BETA and best["gamma"] == GAMMA
        ),
    }

    output_path = reports_dir / f"weight_sweep_{split_name}.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["report_path"] = str(output_path)
    return payload
