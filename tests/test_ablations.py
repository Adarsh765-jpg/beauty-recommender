"""Unit tests for Phase 8 ranking ablations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.ranking import _final_score, default_ranking_config
from engine.types import MixingWeights, RankingConfig, RankingFlags
from src.config import ALPHA, BETA, GAMMA, REPORTS_SMOKE_DIR
from src.evaluation.run_ablation_gate import run_ablation_gate
from tests.conftest import require_clean_reviews


def test_final_score_ablation_flags() -> None:
    base = default_ranking_config()

    no_content = RankingConfig(
        mixing=MixingWeights(alpha=ALPHA, beta=BETA, gamma=GAMMA),
        flags=RankingFlags(use_content=False, use_cohort=True, use_quality=True),
    )
    assert _final_score(0.9, 0.8, 0.7, True, no_content) == pytest.approx(BETA * 0.8 + GAMMA * 0.7)

    no_cohort = RankingConfig(
        mixing=MixingWeights(alpha=ALPHA, beta=BETA, gamma=GAMMA),
        flags=RankingFlags(use_content=True, use_cohort=False, use_quality=True),
    )
    assert _final_score(0.9, 0.8, 0.7, True, no_cohort) == pytest.approx(ALPHA * 0.9 + GAMMA * 0.7)

    no_quality = RankingConfig(
        mixing=MixingWeights(alpha=ALPHA, beta=BETA, gamma=GAMMA),
        flags=RankingFlags(use_content=True, use_cohort=True, use_quality=False),
    )
    assert _final_score(0.9, 0.8, 0.7, True, no_quality) == pytest.approx(ALPHA * 0.9 + BETA * 0.8)

    assert _final_score(0.9, 0.8, 0.7, False, base) == pytest.approx(ALPHA * 0.9 + GAMMA * 0.7)


def test_ablation_gate_smoke() -> None:
    require_clean_reviews()
    result = run_ablation_gate(
        max_queries=8,
        seed=7,
        reports_dir=REPORTS_SMOKE_DIR,
        skip_weight_sweep=True,
        skip_embedding=True,
    )
    report_path = Path(result["report_path"])
    assert report_path.exists()
    assert report_path.parent == REPORTS_SMOKE_DIR
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert "gate" in payload
    assert payload["gate"]["pass"] in {True, False}
    assert payload["queries"] == 8
    assert "full" in payload["ablations"]["ablations"]
    assert "no_cohort" in payload["ablations"]["ablations"]
