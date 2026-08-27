"""Audit reproducibility and spec-number checks."""

from __future__ import annotations

from pathlib import Path

from src.audit.run_audit import run_audit
from src.config import DATA_RAW


def test_audit_reproduces_core_counts() -> None:
    if not (DATA_RAW / "product_info.csv").exists():
        return  # skip when raw data not downloaded locally

    report = run_audit(DATA_RAW)
    assert report["products"]["row_count"] == 8494
    assert report["products"]["skincare_row_count"] == 2420
    assert report["reviews"]["row_count"] == 49977
    assert report["join_coverage"]["reviewed_skincare_product_count"] == 1104
    assert report["reviews"]["reviews_per_reviewer"]["median"] == 1.0


def test_audit_report_files_exist_after_manual_run() -> None:
    json_path = Path("data/audit/audit_report.json")
    if not json_path.exists():
        return
    assert json_path.stat().st_size > 0
