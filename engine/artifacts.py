"""Load precomputed recommendation artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from engine.tfidf import TfidfModel
from src.config import DATA_ARTIFACTS


@dataclass(frozen=True)
class ArtifactBundle:
    catalog: list[dict[str, Any]]
    product_ids: tuple[str, ...]
    id_to_index: dict[str, int]
    tfidf_model: TfidfModel
    tfidf_data: np.ndarray
    tfidf_indices: np.ndarray
    tfidf_indptr: np.ndarray
    meta: dict[str, Any]

    @property
    def product_count(self) -> int:
        return len(self.product_ids)

    def text_similarities(self, profile_vector: np.ndarray) -> np.ndarray:
        return self.tfidf_model.sparse_matvec(
            self.tfidf_data,
            self.tfidf_indices,
            self.tfidf_indptr,
            profile_vector,
        )


def _default_artifacts_dir() -> Path:
    env_path = Path(__file__).resolve().parent.parent / "data" / "artifacts"
    return DATA_ARTIFACTS if DATA_ARTIFACTS.exists() else env_path


def load_artifacts(artifacts_dir: Path | None = None) -> ArtifactBundle:
    root = artifacts_dir or _default_artifacts_dir()

    catalog_path = root / "catalog.json"
    vocab_path = root / "vocabulary.json"
    idf_path = root / "idf.npy"
    tfidf_path = root / "tfidf.npz"
    meta_path = root / "meta.json"

    for path in (catalog_path, vocab_path, idf_path, tfidf_path, meta_path):
        if not path.exists():
            raise FileNotFoundError(f"Missing artifact: {path}")

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    vocabulary = json.loads(vocab_path.read_text(encoding="utf-8"))
    idf = np.load(idf_path)
    tfidf = np.load(tfidf_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    product_ids = tuple(item["product_id"] for item in catalog)
    id_to_index = {product_id: index for index, product_id in enumerate(product_ids)}

    model = TfidfModel(vocabulary=vocabulary, idf=idf, norm=meta.get("tfidf_norm", "l2"))

    return ArtifactBundle(
        catalog=catalog,
        product_ids=product_ids,
        id_to_index=id_to_index,
        tfidf_model=model,
        tfidf_data=tfidf["data"],
        tfidf_indices=tfidf["indices"],
        tfidf_indptr=tfidf["indptr"],
        meta=meta,
    )


@lru_cache(maxsize=1)
def get_artifacts() -> ArtifactBundle:
    return load_artifacts()


def clear_artifact_cache() -> None:
    get_artifacts.cache_clear()
