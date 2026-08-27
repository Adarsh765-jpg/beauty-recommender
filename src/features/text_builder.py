"""Build the TF-IDF text field for a product."""

from __future__ import annotations


def build_product_text(
    product_name: str,
    brand_name: str,
    primary_category: str,
    secondary_category: str,
    tertiary_category: str,
    highlights: list[str],
) -> str:
    """Compose text for TF-IDF.

    Deliberately excludes the raw ingredient list so ``text_similarity`` stays
    decorrelated from ingredient-derived ``concern_match``.
    """
    parts = [
        product_name,
        brand_name,
        primary_category,
        secondary_category,
        tertiary_category,
        *highlights,
    ]
    cleaned = [part.strip() for part in parts if isinstance(part, str) and part.strip()]
    return " ".join(cleaned)
