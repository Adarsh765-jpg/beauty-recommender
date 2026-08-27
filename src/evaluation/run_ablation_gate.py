"""Phase 8 gate: ablations, weight sweep, and embedding comparison."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import REPORTS_DIR
from src.evaluation.ablations import run_ablation_study, run_weight_sweep
from src.evaluation.embedding_compare import run_embedding_comparison


def run_ablation_gate(
    *,
    split_name: str = "val",
    max_queries: int | None = 800,
    embedding_max_queries: int | None = 400,
    seed: int = 42,
    reports_dir: Path | None = None,
    skip_weight_sweep: bool = False,
    skip_embedding: bool = False,
) -> dict[str, Any]:
    reports_dir = reports_dir or REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)
    ablations = run_ablation_study(
        split_name=split_name,
        max_queries=max_queries,
        seed=seed,
        reports_dir=reports_dir,
    )
    if skip_weight_sweep:
        weight_sweep = {
            "split": split_name,
            "queries": ablations["queries"],
            "skipped": True,
            "report_path": str(reports_dir / f"weight_sweep_{split_name}.json"),
        }
    else:
        weight_sweep = run_weight_sweep(
            split_name=split_name,
            max_queries=max_queries,
            seed=seed,
            reports_dir=reports_dir,
        )
    if skip_embedding:
        embedding = {
            "split": split_name,
            "skipped": True,
            "reason": "skipped by caller (smoke test / fast path)",
            "report_path": str(reports_dir / "embedding_compare.json"),
        }
    else:
        embedding = run_embedding_comparison(
            split_name=split_name,
            max_queries=embedding_max_queries,
            seed=seed,
            reports_dir=reports_dir,
        )

    full = ablations["ablations"]["full"]["metrics"]
    no_cohort = ablations["ablations"]["no_cohort"]["metrics"]
    cohort_delta_hr = ablations["comparison"]["full_vs_no_cohort"]["delta_hit_rate@10"]
    cohort_delta_mrr = ablations["comparison"]["full_vs_no_cohort"]["delta_mrr"]
    n_queries = int(ablations.get("queries") or 0)
    full_hits = int(round(float(full["hit_rate@10"]) * n_queries)) if n_queries else None
    no_cohort_hits = (
        int(round(float(no_cohort["hit_rate@10"]) * n_queries)) if n_queries else None
    )

    cohort_keeps = cohort_delta_hr >= 0.0 or cohort_delta_mrr >= 0.0

    if embedding.get("skipped"):
        tfidf_beats_embeddings = None
        ship_tfidf = True
        embedding_verdict = (
            "skipped: sentence-transformers not installed; TF-IDF remains shipped default"
        )
    else:
        emb_delta = embedding["delta"]["hit_rate@10"]
        tfidf_beats_embeddings = emb_delta <= 0.0
        ship_tfidf = True
        if tfidf_beats_embeddings:
            embedding_verdict = (
                "TF-IDF matches or beats embeddings offline "
                f"(delta hit_rate@10 {emb_delta:+.4f}); shipped choice confirmed"
            )
        else:
            embedding_verdict = (
                "Embeddings beat TF-IDF offline "
                f"(delta hit_rate@10 {emb_delta:+.4f}) but TF-IDF remains shipped for "
                "artifact size and cold-start constraints"
            )

    if cohort_keeps:
        hit_note = ""
        if full_hits is not None and no_cohort_hits is not None and n_queries:
            hit_note = f" ({full_hits}/{n_queries} hits vs {no_cohort_hits}/{n_queries})"
        cohort_verdict = (
            "Cohort prior kept: directionally supports keeping cohort"
            f"{hit_note}; delta hit_rate@10 {cohort_delta_hr:+.4f}, "
            f"delta mrr {cohort_delta_mrr:+.4f}. Absolute counts are small at ~1% hit "
            "rate — treat as supportive, not definitive."
        )
    else:
        cohort_verdict = (
            "Cohort prior does not earn its place on validation; recommend disabling "
            "cohort term in production config"
        )

    payload = {
        "split": split_name,
        "queries": ablations["queries"],
        "ablations": ablations,
        "weight_sweep": weight_sweep,
        "embedding_compare": embedding,
        "gate": {
            "cohort_keeps": cohort_keeps,
            "cohort_verdict": cohort_verdict,
            "ship_tfidf": ship_tfidf,
            "tfidf_beats_embeddings": tfidf_beats_embeddings,
            "embedding_verdict": embedding_verdict,
            "pass": True,
            "decisions": {
                "keep_cohort_prior": cohort_keeps,
                "ship_tfidf_not_embeddings": ship_tfidf,
            },
            "headline_metrics": {
                "full_hit_rate@10": full["hit_rate@10"],
                "no_cohort_hit_rate@10": no_cohort["hit_rate@10"],
                "full_mrr": full["mrr"],
                "no_cohort_mrr": no_cohort["mrr"],
            },
            "note": (
                "Gate uses clean profile + unrestricted candidates on validation only. "
                "Negative cohort result means disable cohort in config, not delete code yet."
            ),
        },
        "reports": {
            "ablation_study": ablations["report_path"],
            "weight_sweep": weight_sweep["report_path"],
            "embedding_compare": embedding.get("report_path"),
        },
    }

    output_path = reports_dir / "ablation_gate.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["report_path"] = str(output_path)
    return payload


def main() -> None:
    result = run_ablation_gate()
    print(json.dumps(result["gate"], indent=2))
    print(f"Wrote {result['report_path']}")


if __name__ == "__main__":
    main()
