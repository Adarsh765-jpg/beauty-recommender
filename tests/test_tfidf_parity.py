"""TF-IDF parity between scikit-learn fit and numpy runtime transform."""

from __future__ import annotations

import json

import numpy as np
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from engine.analyzer import tokenize
from engine.tfidf import TfidfModel
from src.config import (
    DATA_ARTIFACTS,
    TFIDF_NORM,
    TFIDF_SMOOTH_IDF,
    TFIDF_SUBLINEAR_TF,
    TFIDF_USE_IDF,
)


@pytest.fixture(scope="module")
def sample_texts() -> list[str]:
    catalog_path = DATA_ARTIFACTS / "catalog.json"
    if not catalog_path.exists():
        pytest.skip("catalog.json not built yet")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    return [item["text"] for item in catalog[:200]]


def test_numpy_transform_matches_sklearn(sample_texts: list[str]) -> None:
    vectorizer = TfidfVectorizer(
        analyzer=tokenize,
        lowercase=False,
        norm=TFIDF_NORM,
        use_idf=TFIDF_USE_IDF,
        smooth_idf=TFIDF_SMOOTH_IDF,
        sublinear_tf=TFIDF_SUBLINEAR_TF,
    )
    sklearn_matrix = vectorizer.fit_transform(sample_texts).toarray()
    model = TfidfModel(
        vocabulary=vectorizer.vocabulary_,
        idf=vectorizer.idf_.astype(np.float32),
        norm=TFIDF_NORM,
    )
    numpy_matrix = model.transform_many(sample_texts)

    np.testing.assert_allclose(numpy_matrix, sklearn_matrix, rtol=1e-5, atol=1e-6)


def test_saved_sparse_matrix_matches_runtime_transform(sample_texts: list[str]) -> None:
    vocab_path = DATA_ARTIFACTS / "vocabulary.json"
    idf_path = DATA_ARTIFACTS / "idf.npy"
    tfidf_path = DATA_ARTIFACTS / "tfidf.npz"
    if not all(path.exists() for path in (vocab_path, idf_path, tfidf_path)):
        pytest.skip("TF-IDF artifacts not built yet")

    vocabulary = json.loads(vocab_path.read_text(encoding="utf-8"))
    idf = np.load(idf_path)
    saved = np.load(tfidf_path)

    model = TfidfModel(vocabulary=vocabulary, idf=idf, norm=TFIDF_NORM)
    numpy_matrix = model.transform_many(sample_texts)

    for row in range(len(sample_texts)):
        dense = np.zeros(model.vocab_size, dtype=np.float32)
        start = int(saved["indptr"][row])
        end = int(saved["indptr"][row + 1])
        dense[saved["indices"][start:end]] = saved["data"][start:end]
        np.testing.assert_allclose(dense, numpy_matrix[row], rtol=1e-5, atol=1e-6)
