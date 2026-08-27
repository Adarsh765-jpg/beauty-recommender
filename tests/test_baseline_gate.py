"""Smoke test for Phase 6 baseline gate."""

from __future__ import annotations

import json
from pathlib import Path

from src.config import REPORTS_SMOKE_DIR
from src.evaluation.run_baseline_gate import run_baseline_gate


def test_baseline_gate_smoke() -> None:
    result = run_baseline_gate(
        max_queries=10,
        seed=11,
        reports_dir=REPORTS_SMOKE_DIR,
        skip_tuning=True,
    )
    report_path = Path(result["report_path"])
    assert report_path.exists()
    assert report_path.parent == REPORTS_SMOKE_DIR
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert "gate" in payload
    assert payload["gate"]["pass"] in {True, False}
    assert payload["queries"] == 10
