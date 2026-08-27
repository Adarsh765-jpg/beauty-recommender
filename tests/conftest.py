"""Shared pytest helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config import DATA_INTERIM


def require_clean_reviews() -> Path:
    """Skip when interim reviews are absent (typical on a fresh CI checkout)."""
    path = DATA_INTERIM / "reviews_clean.parquet"
    if not path.exists():
        pytest.skip("cleaned reviews missing; run preprocessing first")
    return path
