"""Validate concern rules and exclusion detection."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.config import CONCERN_REVIEW_VOCAB, CONCERNS
from src.features.feature_engineering import ProductRecord
from src.features.text_builder import build_product_text


def _review_mentions_concern(text: str, concern: str) -> bool:
    vocab = CONCERN_REVIEW_VOCAB.get(concern, ())
    lowered = text.lower()
    return any(term in lowered for term in vocab)


def validate_concern_rules(
    catalog: list[ProductRecord],
    reviews: pd.DataFrame,
    min_reviews_per_bucket: int = 20,
) -> dict[str, Any]:
    """Compare concern vocabulary rates in tagged vs untagged product reviews."""
    concern_by_product: dict[str, set[str]] = {
        record["product_id"]: set(record["derived_concerns"]) for record in catalog
    }

    review_rows: list[dict[str, Any]] = []
    for _, row in reviews.iterrows():
        pid = str(row["product_id"])
        text = str(row.get("review_text") or "")
        if not text.strip():
            continue
        review_rows.append(
            {
                "product_id": pid,
                "text": text,
                "concerns": concern_by_product.get(pid, set()),
            }
        )

    results: dict[str, Any] = {}
    for concern in CONCERNS:
        tagged_texts = [r["text"] for r in review_rows if concern in r["concerns"]]
        untagged_texts = [r["text"] for r in review_rows if concern not in r["concerns"]]

        tagged_count = len(tagged_texts)
        untagged_count = len(untagged_texts)
        if tagged_count < min_reviews_per_bucket or untagged_count < min_reviews_per_bucket:
            results[concern] = {
                "status": "insufficient_sample",
                "tagged_reviews": len(tagged_texts),
                "untagged_reviews": len(untagged_texts),
            }
            continue

        tagged_rate = (
            sum(_review_mentions_concern(text, concern) for text in tagged_texts) / tagged_count
        )
        untagged_rate = (
            sum(_review_mentions_concern(text, concern) for text in untagged_texts) / untagged_count
        )
        lift = tagged_rate - untagged_rate
        results[concern] = {
            "status": "ok",
            "tagged_reviews": len(tagged_texts),
            "untagged_reviews": len(untagged_texts),
            "tagged_vocab_rate": round(tagged_rate, 4),
            "untagged_vocab_rate": round(untagged_rate, 4),
            "lift": round(lift, 4),
            "passes_separation": lift > 0.02,
        }

    return results


def _ground_truth_exclusion(ingredients: list[str], flag: str) -> bool:
    blob = " ".join(ingredients).lower()
    if flag == "fragrance":
        return any(term in blob for term in ("fragrance", "parfum", "perfume"))
    if flag == "drying_alcohol":
        return any(
            term in blob
            for term in (
                "alcohol denat",
                "sd alcohol",
                "denatured alcohol",
                "isopropyl alcohol",
                "ethanol",
            )
        )
    if flag == "paraben":
        return "paraben" in blob
    if flag == "sulfate":
        sulfate_terms = ("sodium lauryl sulfate", "sodium laureth sulfate", "sls")
        return any(term in blob for term in sulfate_terms)
    return False


def audit_exclusion_flags(catalog: list[ProductRecord]) -> dict[str, Any]:
    """Measure recall on products with known exclusion ingredients."""
    audits: dict[str, Any] = {}
    for flag in ("fragrance", "drying_alcohol"):
        positives = [r for r in catalog if _ground_truth_exclusion(r["ingredients"], flag)]
        if not positives:
            audits[flag] = {"status": "no_positives", "recall": None}
            continue

        detected = sum(1 for record in positives if record["exclusion_flags"].get(flag, False))
        recall = detected / len(positives)
        audits[flag] = {
            "status": "ok",
            "positive_products": len(positives),
            "detected": detected,
            "recall": round(recall, 4),
            "passes_recall_gate": recall >= 0.9,
        }

    return audits


def verify_text_excludes_ingredients(catalog: list[ProductRecord]) -> dict[str, Any]:
    """Ensure TF-IDF text is composed only from marketing fields."""
    violations = 0
    checked = 0

    for record in catalog:
        expected = build_product_text(
            product_name=record["product_name"],
            brand_name=record["brand"],
            primary_category=record["primary_category"],
            secondary_category=record["secondary_category"],
            tertiary_category=record["tertiary_category"],
            highlights=record["highlights"],
        )
        if not expected:
            continue
        checked += 1
        if record["text"] != expected:
            violations += 1

    return {
        "products_checked": checked,
        "violations": violations,
        "passes": violations == 0,
    }
