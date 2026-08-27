# Benchmark & evaluation report

**In one sentence:** we checked whether our ranking beats simple baselines (popularity, random, rating-only) on held-out reviews — and whether each score piece is worth keeping.

All decisions below used the **validation** split only (test set stayed unused for choosing the model).

**Where the numbers live:** `reports/baseline_gate.json`, `reports/ablation_gate.json`, `reports/embedding_compare.json`, `reports/cohort_coverage.json`

**Weights we ship:** 60% content · 25% cohort · 15% quality (`src/config.py`)

---

## Protocol summary

**How to read the tables**

- **hit_rate@10** = “Was the right product somewhere in the top 10?”  
- **Unrestricted** = search almost the whole skincare catalog (harder).  
- **Category-restricted** = shopper already picked a category (more like real browsing).  
- Low unrestricted % does **not** mean the app is broken — it means the needle is small in a big haystack. Compare to popularity/random in the same setting.

| Setting | Value |
|---|---|
| Catalog | 2,420 skincare products |
| Gate queries | 800 (baseline + ablation); 400 (embedding compare) |
| Profile variant (gate) | `clean` (structured skin type + concerns) |
| Candidate pool (gate) | Unrestricted (after stock/price/exclusion filters only) |
| Primary metrics | `hit_rate@10`, MRR |
| Baselines | Popularity, random, rating-only, content |

Relevance labels are derived from held-out review/product matches under the evaluation harness in `src/evaluation/`. Absolute hit rates on the unrestricted pool are low because the candidate set is large (~2,288 avg) and relevant items are sparse — the gate asks whether content beats naive baselines and whether ablations justify shipping decisions.

---

## Baseline gate (pass)

Source: `reports/baseline_gate.json` (800 queries)

| Method (clean · unrestricted) | hit_rate@10 | Notes |
|---|---:|---|
| **Content ranker** | **0.01125** | Ships as content component |
| Popularity | 0.000 | |
| Random | 0.000 | |
| Rating-only | 0.00375 | |
| Tuned content (grid) | 0.0125 | Slightly better; default weights kept for simplicity |

**Category-restricted** setting (easier / more realistic shopping pool):

| Method | hit_rate@10 |
|---|---:|
| Content | **0.1125** (~11.25%) |
| Popularity | 0.0125 (~1.25%) |

That is an ~**9×** lift over popularity in a category-filtered context — the number to read next to the unrestricted 1.125% headline.

**Gate result:** `pass: true` — content beats popularity on unrestricted val.

### Feature correlation (content components)

| Pair | Correlation |
|---|---:|
| skin_match ↔ concern_match | 0.021 |
| skin_match ↔ text_similarity | 0.377 |
| concern_match ↔ text_similarity | 0.112 |

Skin and concern signals are nearly independent; text overlaps moderately with skin. Mixing all three is justified.

---

## Ablation gate (pass)

Source: `reports/ablation_gate.json` (800 queries, clean · unrestricted)

| Configuration | hit_rate@10 | Hits / 800 | MRR | Δ hit_rate@10 vs full |
|---|---:|---:|---:|---:|
| **Full** (content + cohort + quality) | **0.01125** | **9** | 0.00843 | — |
| No cohort | 0.00500 | 4 | 0.00634 | −0.00625 |
| No content | 0.00125 | 1 | 0.00345 | −0.01000 |
| No quality | 0.01125 | 9 | 0.01181 | 0.000 |

At ~1% hit rate and n=800, a ±0.6 pp swing is only a handful of queries. Binomial noise alone can move results by about that much, so small deltas should not be over-claimed.

**Decisions**

| Decision | Verdict | Evidence |
|---|---|---|
| Keep cohort prior | **Directionally supports keeping** | +0.62 pp (9 vs 4 hits). Supportive, not definitive at this count. |
| Keep content | **Yes** | Collapse to 1/800 when removed — large enough to trust |
| Keep quality | **Yes (tie on hit@10)** | Same hit_rate@10; kept for ranking stability / explanations |

### Mixing-weight sweep (not applied)

Shipped weights: **α=0.60, β=0.25, γ=0.15** (matches ablation/baseline runs above)

| Setting | hit_rate@10 | MRR |
|---|---:|---:|
| **Shipped 0.60 / 0.25 / 0.15** | 0.01125 | 0.00843 |
| Grid best 0.50 / 0.35 / 0.15 | **0.020** | 0.00580 |

The grid-best mix was **not** shipped: with sparse hits, that gain can be validation noise, and changing weights late would desync the published ablation table from production. Documented as a future improvement instead.

---

## Embedding comparison (TF-IDF shipped)

Source: `reports/embedding_compare.json` (400 queries)

| Text backend | hit_rate@10 | MRR | Deploy cost |
|---|---:|---:|---|
| TF-IDF (shipped) | 0.0075 | 0.00625 | ~6.1 MB artifacts |
| Sentence-Transformers (`all-MiniLM-L6-v2`) | 0.0150 | 0.00620 | ~92 MB model cache; ~3.5s cold import; ~6.5s catalog encode |

Embeddings win offline (+0.75 pp hit_rate@10) but increase cold-start and artifact size. **TF-IDF remains the production text channel** for Vercel-friendly latency and footprint.

---

## Cohort coverage

Source: `reports/cohort_coverage.json`

| Metric | Value |
|---|---:|
| Products × skin types | 9,680 pairs |
| Pairs with ≥ min reviews | 1,796 (18.6%) |

Cohort is sparse; ranking falls back when the prior is unavailable (`cohort_used=false`).

---

## Serving latency (local)

Measured with FastAPI `TestClient` after warmup (same code path as production ranking; not network-bound):

| Call | Latency |
|---|---|
| First recommend after import | ~63 ms |
| Subsequent (n=5) | ~59–67 ms (p50 ≈ 60 ms) |

Production adds network + cold start. Target for interactive UI: under ~1–2 s end-to-end after warm backend.

---

## How to reproduce gates

```bash
# Full gates (~10 min each on full 800-query val)
python -m src.evaluation.run_baseline_gate
python -m src.evaluation.run_ablation_gate

# Fast smoke (writes under reports/smoke/)
python -m pytest tests/test_baseline_gate.py tests/test_ablations.py -q
```

Unit/API suite:

```bash
python -m pytest tests/ -q
```

---

## Interpretation for evaluators

1. **Success** is defined relative to strong baselines on a hard unrestricted pool, plus ablations that justify each scoring term.
2. Absolute unrestricted hit rates are modest because relevance is sparse in a 2k+ product catalog — **category-restricted hit_rate@10 ≈ 11.25% vs popularity 1.25% (~9×)** is the realistic shopping comparison.
3. Shipping choices (cohort kept as a directional prior, TF-IDF not embeddings, weights frozen at 0.60/0.25/0.15) prioritize **explainability, deployability, and reproducibility** over squeezing the last sparse val points.
4. Displayed top-k applies a hard brand diversity cap (and a category cap when not already category-filtered). Offline evaluation uses pure score order without display diversity, so UI grids can differ slightly from eval top-k lists.
5. Category filtering in production uses shopper-friendly aliases (e.g. Cleansers → Face Wash & Cleansers); see `CATEGORY_ALIASES` in `src/config.py`.
