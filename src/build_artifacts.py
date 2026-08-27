"""Build deployment artifacts: catalog, TF-IDF matrix, vocabulary, and metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from engine.analyzer import tokenize
from engine.quality import compute_catalog_rating_prior
from src.cohort.build_cohort_stats import build_cohort_stats
from src.config import (
    ALPHA,
    ARTIFACT_SIZE_BUDGET_BYTES,
    BETA,
    DATA_ARTIFACTS,
    DATA_INTERIM,
    GAMMA,
    REPORTS_DIR,
    TFIDF_NORM,
    TFIDF_SMOOTH_IDF,
    TFIDF_SUBLINEAR_TF,
    TFIDF_USE_IDF,
    W_CONCERN,
    W_SKIN,
    W_TEXT,
)
from src.features.feature_engineering import catalog_summary
from src.features.run_features import run_feature_engineering


def _fit_tfidf(texts: list[str]) -> tuple[TfidfVectorizer, Any]:
    vectorizer = TfidfVectorizer(
        analyzer=tokenize,
        lowercase=False,
        norm=TFIDF_NORM,
        use_idf=TFIDF_USE_IDF,
        smooth_idf=TFIDF_SMOOTH_IDF,
        sublinear_tf=TFIDF_SUBLINEAR_TF,
    )
    matrix = vectorizer.fit_transform(texts)
    return vectorizer, matrix


def _file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def build_artifacts(
    *,
    output_dir: Path | None = None,
    rebuild_catalog: bool = True,
) -> dict[str, Any]:
    output_dir = output_dir or DATA_ARTIFACTS
    output_dir.mkdir(parents=True, exist_ok=True)

    if rebuild_catalog:
        run_feature_engineering(output_dir=output_dir)

    catalog_path = output_dir / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    texts = [item["text"] for item in catalog]

    vectorizer, matrix = _fit_tfidf(texts)
    csr = matrix.tocsr().astype(np.float32)

    vocabulary = vectorizer.vocabulary_
    idf = vectorizer.idf_.astype(np.float32)

    vocab_path = output_dir / "vocabulary.json"
    idf_path = output_dir / "idf.npy"
    tfidf_path = output_dir / "tfidf.npz"
    meta_path = output_dir / "meta.json"

    vocab_path.write_text(json.dumps(vocabulary, indent=2), encoding="utf-8")
    np.save(idf_path, idf)
    np.savez(
        tfidf_path,
        data=csr.data,
        indices=csr.indices,
        indptr=csr.indptr,
        shape=np.array(csr.shape, dtype=np.int64),
    )

    summary = catalog_summary(catalog)
    catalog_mean_rating = compute_catalog_rating_prior(catalog)
    catalog_product_ids = {str(item["product_id"]) for item in catalog}

    cohort_stats: dict[str, Any] = {}
    reviews_path = DATA_INTERIM / "reviews_clean.parquet"
    if reviews_path.exists():
        reviews = pd.read_parquet(reviews_path)
        cohort_stats = build_cohort_stats(reviews, catalog_product_ids, split_name="train")
        reports_dir = REPORTS_DIR
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "cohort_coverage.json").write_text(
            json.dumps(cohort_stats["coverage"], indent=2),
            encoding="utf-8",
        )

    artifact_files = {
        "catalog.json": _file_size(catalog_path),
        "vocabulary.json": _file_size(vocab_path),
        "idf.npy": _file_size(idf_path),
        "tfidf.npz": _file_size(tfidf_path),
    }
    total_bytes = sum(artifact_files.values())

    meta = {
        "product_count": len(catalog),
        "vocab_size": len(vocabulary),
        "tfidf_norm": TFIDF_NORM,
        "catalog_mean_rating": catalog_mean_rating,
        "weights": {
            "w_skin": W_SKIN,
            "w_concern": W_CONCERN,
            "w_text": W_TEXT,
            "alpha": ALPHA,
            "beta": BETA,
            "gamma": GAMMA,
        },
        "catalog_summary": summary,
        "artifact_files_bytes": artifact_files,
        "artifact_total_bytes": total_bytes,
        "artifact_budget_bytes": ARTIFACT_SIZE_BUDGET_BYTES,
        "within_budget": total_bytes <= ARTIFACT_SIZE_BUDGET_BYTES,
        "cohort_stats": cohort_stats,
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return {
        "output_dir": str(output_dir),
        "product_count": len(catalog),
        "vocab_size": len(vocabulary),
        "artifact_total_bytes": total_bytes,
        "within_budget": total_bytes <= ARTIFACT_SIZE_BUDGET_BYTES,
        "meta_path": str(meta_path),
    }


def main() -> None:
    result = build_artifacts()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
