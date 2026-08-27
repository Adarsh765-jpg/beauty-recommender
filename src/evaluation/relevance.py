"""Relevance labels for held-out review evaluation."""

from __future__ import annotations


def is_relevant(is_recommended: bool | None, rating: int) -> bool:
    """Primary label from ``is_recommended``; fallback to rating >= 4."""
    if is_recommended is not None:
        return bool(is_recommended)
    return rating >= 4
