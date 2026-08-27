"""Offline sentence-transformer comparison vs shipped TF-IDF text similarity."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, cast

import numpy as np

from engine.artifacts import load_artifacts
from engine.content_ranker import build_profile_text
from engine.ranking import TextSimilarityFn
from engine.types import BeautyProfile
from src.config import DATA_ARTIFACTS, REPORTS_DIR
from src.evaluation.evaluate import run_evaluation

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _artifact_payload_bytes(artifacts_dir: Path) -> dict[str, int]:
    files = ("catalog.json", "vocabulary.json", "idf.npy", "tfidf.npz", "meta.json")
    sizes = {
        name: (artifacts_dir / name).stat().st_size
        for name in files
        if (artifacts_dir / name).exists()
    }
    sizes["total_bytes"] = sum(sizes.values())
    return sizes


def _build_embedding_similarity_fn(
    product_embeddings: np.ndarray,
    model: Any,
) -> TextSimilarityFn:
    profile_cache: dict[str, np.ndarray] = {}

    def _profile_embedding(profile_text: str) -> np.ndarray:
        cached = profile_cache.get(profile_text)
        if cached is not None:
            return cached
        vector = np.asarray(model.encode(profile_text, normalize_embeddings=True), dtype=np.float32)
        profile_cache[profile_text] = vector
        return vector

    def similarity_fn(profile: BeautyProfile, eligible_indices: np.ndarray) -> np.ndarray:
        profile_vector = _profile_embedding(build_profile_text(profile))
        product_vectors = product_embeddings[eligible_indices]
        raw = product_vectors @ profile_vector
        return cast(np.ndarray, np.clip(raw, 0.0, 1.0).astype(np.float32))

    return similarity_fn


def run_embedding_comparison(
    *,
    split_name: str = "val",
    max_queries: int | None = 400,
    seed: int = 42,
    profile_variant: str = "clean",
    candidate_variant: str = "unrestricted",
    reports_dir: Path | None = None,
) -> dict[str, Any]:
    reports_dir = reports_dir or REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)
    variant_key = f"{profile_variant}__{candidate_variant}"
    artifacts_dir = DATA_ARTIFACTS
    tfidf_bytes = _artifact_payload_bytes(artifacts_dir)

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        payload = {
            "split": split_name,
            "skipped": True,
            "reason": "sentence-transformers not installed (offline dev dependency)",
            "tfidf_artifact_bytes": tfidf_bytes,
        }
        output_path = reports_dir / "embedding_compare.json"
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        payload["report_path"] = str(output_path)
        return payload

    import_start = time.perf_counter()
    model = SentenceTransformer(EMBEDDING_MODEL)
    import_seconds = time.perf_counter() - import_start

    cache_root = Path.home() / ".cache" / "huggingface" / "hub"
    model_size_bytes = 0
    if cache_root.exists():
        for path in cache_root.rglob("*"):
            if path.is_file() and "MiniLM-L6-v2" in str(path):
                model_size_bytes += path.stat().st_size

    artifacts = load_artifacts()
    product_texts = [item["text"] for item in artifacts.catalog]
    encode_start = time.perf_counter()
    product_embeddings = np.asarray(
        model.encode(product_texts, normalize_embeddings=True, show_progress_bar=False),
        dtype=np.float32,
    )
    encode_seconds = time.perf_counter() - encode_start

    similarity_fn = _build_embedding_similarity_fn(product_embeddings, model)

    tfidf_eval = run_evaluation(
        split_name=split_name,
        max_queries=max_queries,
        seed=seed,
        rankers=("content",),
        profile_variants=(profile_variant,),  # type: ignore[arg-type]
        candidate_variants=(candidate_variant,),  # type: ignore[arg-type]
        output_path=reports_dir / f"embedding_compare_tfidf_{split_name}.json",
    )
    embedding_eval = run_evaluation(
        split_name=split_name,
        max_queries=max_queries,
        seed=seed,
        rankers=("content",),
        profile_variants=(profile_variant,),  # type: ignore[arg-type]
        candidate_variants=(candidate_variant,),  # type: ignore[arg-type]
        text_similarity_fn=similarity_fn,
        output_path=reports_dir / f"embedding_compare_st_{split_name}.json",
    )

    tfidf_metrics = tfidf_eval["variants"][variant_key]["content"]
    embedding_metrics = embedding_eval["variants"][variant_key]["content"]

    payload = {
        "split": split_name,
        "variant_key": variant_key,
        "queries": tfidf_eval["queries"],
        "skipped": False,
        "model": EMBEDDING_MODEL,
        "deployment_cost": {
            "tfidf_artifact_bytes": tfidf_bytes,
            "embedding_model_cache_bytes_estimate": model_size_bytes,
            "cold_start_import_seconds": round(import_seconds, 3),
            "offline_catalog_encode_seconds": round(encode_seconds, 3),
            "note": (
                "Embeddings are offline-only. Shipped runtime uses TF-IDF artifacts "
                f"({tfidf_bytes['total_bytes']:,} bytes total)."
            ),
        },
        "tfidf": {
            "hit_rate@10": tfidf_metrics["hit_rate@10"],
            "mrr": tfidf_metrics["mrr"],
        },
        "sentence_transformer": {
            "hit_rate@10": embedding_metrics["hit_rate@10"],
            "mrr": embedding_metrics["mrr"],
        },
        "delta": {
            "hit_rate@10": embedding_metrics["hit_rate@10"] - tfidf_metrics["hit_rate@10"],
            "mrr": embedding_metrics["mrr"] - tfidf_metrics["mrr"],
        },
        "reports": {
            "tfidf": tfidf_eval["report_path"],
            "sentence_transformer": embedding_eval["report_path"],
        },
    }

    output_path = reports_dir / "embedding_compare.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["report_path"] = str(output_path)
    return payload
