# Beauty Recommender

Explainable, personalized skincare recommendations on the Sephora product catalog.

**Live:** https://beauty-recommender.vercel.app  
**Repo:** https://github.com/Adarsh765-jpg/beauty-recommender

---

## Problem & motivation

Beauty shoppers face a huge catalog and vague “best for you” claims. This system ranks Sephora skincare for a skin profile and shows **evidence-backed reasons** for each pick — not a black box.

Inspired by Nykaa/Sephora quiz flows, with an emphasis on **explainability** over opaque collaborative filtering.

---

## What it does

1. Collect skin type, concerns, ingredient exclusions, budget, and category
2. Hard-filter the catalog (stock, price, category, exclusions)
3. Rank with a hybrid score: content fit + skin-type cohort prior + review quality
4. Attach gated explanations (only claims backed by evidence)
5. Serve results through a FastAPI API and a Next.js quiz UI

---

## Architecture

```
Browser (Next.js)
    │  POST /api/recommend
    ▼
Vercel rewrite ──► FastAPI (backend/)
                       │
                       ▼
              engine/ ranking + explain
                       │
                       ▼
         data/artifacts (TF-IDF, catalog, cohort meta)
```

| Layer | Role |
|---|---|
| `frontend/` | Quiz UI, product cards, Why-this panel |
| `backend/` | FastAPI `/api/health`, `/api/schema`, `/api/recommend` |
| `engine/` | Constraints, TF-IDF content ranker, cohort, quality, explanations |
| `src/` | Offline data audit, preprocessing, features, evaluation gates |
| `data/artifacts/` | Precomputed catalog + TF-IDF (no pandas at request time) |
| `scripts/prepare_backend.py` | Copies `engine/`, `src/config.py`, artifacts into `backend/` for Vercel |

---

## Recommendation methodology

**Content score**

```
content = 0.34·skin_match + 0.34·concern_match + 0.32·text_similarity
```

**Final score** (when cohort signal is available)

```
final = 0.60·content + 0.25·cohort + 0.15·quality
```

Otherwise cohort is dropped and content + quality are used.

Explanations only emit claims that pass evidence gates (e.g. skin type in `suited_skin_types`, concern overlap, cohort threshold, review quality).

---

## Dataset

- Source: [Sephora Products and Skincare Reviews](https://www.kaggle.com/datasets/nadyinky/sephora-products-and-skincare-reviews) (via [nadyinky/sephora-analysis](https://github.com/nadyinky/sephora-analysis))
- Runtime catalog: **2,420** skincare products in `data/artifacts/catalog.json`
- Samples under `data/sample/` for smoke/offline checks
- **No product image URLs** in the source CSV — UI uses placeholders (see Limitations)

---

## Tech stack

- **Frontend:** Next.js 16, React 19, Tailwind CSS 4
- **Backend:** FastAPI, NumPy
- **Offline ML:** pandas / scikit-learn style TF-IDF pipeline in `src/` + `engine/tfidf.py`
- **Deploy:** Vercel Services (`vercel.json` frontend + backend)
- **Tests:** pytest, mypy, ruff

---

## Local setup

### Prerequisites

- Python 3.12+
- Node.js 20+

### Backend

```bash
pip install -r requirements-dev.txt
pip install -r backend/requirements.txt
python scripts/prepare_backend.py
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npx next dev -p 3000
```

Open http://localhost:3000 — the Next config proxies `/api/*` to port 8000 locally.

### API smoke

```bash
curl http://127.0.0.1:8000/api/health
curl -X POST http://127.0.0.1:8000/api/recommend ^
  -H "Content-Type: application/json" ^
  -d "{\"skin_type\":\"dry\",\"concerns\":[\"hydration\"],\"budget_max_usd\":80,\"top_k\":5}"
```

Interactive docs: http://127.0.0.1:8000/api/docs

---

## Evaluation

Offline gates live under `reports/`. Human-readable summary: [`docs/BENCHMARK.md`](docs/BENCHMARK.md).

| Report | Purpose |
|---|---|
| `baseline_gate.json` | Content vs popularity / random / rating on val |
| `ablation_gate.json` | Ablate content / cohort / quality; weight sweep |
| `embedding_compare.json` | TF-IDF vs sentence-transformers cost/quality |
| `cohort_coverage.json` | Fraction of skin-type pairs with enough reviews |

**Headline decisions:** content beats popularity (gate pass); keep cohort prior (+0.62 pp hit_rate@10); ship TF-IDF over embeddings for size/cold-start.

Run tests:

```bash
python -m pytest tests/ -q
python -m mypy backend engine src tests
python -m ruff check .
```

---

## Test cases

See [`docs/TEST_CASES.md`](docs/TEST_CASES.md) for successful and failure scenarios.

---

## Assumptions & design decisions

- Cold-start / profile-based ranking (no user history graph)
- Hard filters never become soft score penalties
- Precompute artifacts so request path stays lightweight on Vercel
- Evidence-gated explanations over unrestricted LLM copy
- Typographic / placeholder product visuals until images are enriched

---

## Known limitations

- No product images in the dataset (placeholders in UI)
- Cohort coverage is uneven for rare skin-type × product cells (~18.6% of pairs meet the review minimum)
- Ingredient exclusion rules are keyword-based, not dermatologist-validated
- Category filter is exact secondary/tertiary match
- `filtered_count` in the API = products **rejected** by filters; `candidate_count` = eligible
- Absolute unrestricted hit rates are low; see [`docs/BENCHMARK.md`](docs/BENCHMARK.md) for interpretation

---

## Future improvements

- Offline image enrichment (Sephora SKU → self-hosted assets)
- Tuned mixing weights from val sweep (0.50/0.35/0.15 looked stronger offline)
- Routine builder (cleanser → treatment → moisturizer)
- A/B explanation formats and diversity constraints

---

## Bonus: Nykaa-inspired comparison

| | Nykaa / Sephora | This system |
|---|---|---|
| **Similar** | Skin quiz, filter chips, product grid, ratings/price | Same interaction pattern |
| **Different** | Purchase graph, personalization at scale, real images | Hybrid content+cohort+quality with explicit score breakdown |
| **Limitation** | — | No images, no live inventory, smaller offline catalog slice |
| **Next** | — | Images, routines, learned ranking, richer exclusions |

---

## Deploy notes

1. Ensure `data/artifacts/` is committed (catalog, tfidf, meta, vocabulary, idf)
2. `vercel.json` runs `python ../scripts/prepare_backend.py` on backend install
3. Do **not** rely on Next.js rewriting `/api` to localhost in production (`VERCEL` env skips that rewrite)
