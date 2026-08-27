# Beauty Recommender

A skincare quiz that recommends Sephora products and shows **why** each pick fits.

**Try it:** https://beauty-recommender.vercel.app  
**Code:** https://github.com/Adarsh765-jpg/beauty-recommender

### Try it live
1. Open the live link (first load may take a moment on Vercel)  
2. Click **Quick Demo** (or pick Dry + Hydration, budget $80)  
3. Tap a product and read **Why this pick**

More detail (optional): [How it works](docs/ARCHITECTURE.md) · [API](docs/API.md) · [Numbers](docs/BENCHMARK.md) · [Test scenarios](docs/TEST_CASES.md)

---

## What problem does this solve?

Shopping for skincare is hard: huge catalogs, vague “best for you” claims, and no purchase history on a first visit.

This app asks a short quiz (skin type, concerns, budget, exclusions) and returns ranked products with clear reasons — not a black box.

---

## How it works (simple version)

```text
Quiz answers → drop products that break rules (budget, stock, ingredients)
            → score what’s left (fit + similar shoppers + reviews)
            → show top results with short explanations
```

Three score pieces (when available):

| Piece | In plain English |
|---|---|
| **Content** | Does it match your skin and concerns? (also text similarity) |
| **Cohort** | Do people with the same skin type tend to like it? |
| **Quality** | Is it well reviewed? (careful with tiny review counts) |

Final mix we ship: **60% content · 25% cohort · 15% quality**.  
Cohort only applies when there is enough same-skin-type evidence (see Limits). Other weight mixes: [BENCHMARK](docs/BENCHMARK.md). Diagrams: [ARCHITECTURE](docs/ARCHITECTURE.md).

Rules like “no fragrance” or “under $80” are **hard stops** — they never get weakly scored away.

---

## Dataset

Public Sephora skincare data ([Kaggle](https://www.kaggle.com/datasets/nadyinky/sephora-products-and-skincare-reviews) / [GitHub](https://github.com/nadyinky/sephora-analysis)):

- **2,420** skincare products in the live catalog  
- Reviews used offline to learn “people with dry skin liked X” signals and to measure quality  
- Small samples in `data/sample/` so a fresh clone can smoke-test  

---

## Built with

- **UI:** Next.js + React + Tailwind  
- **API:** FastAPI  
- **Scoring:** NumPy + precomputed files (TF-IDF text match)  
- **Host:** Vercel  
- **Checks:** pytest, mypy, ruff, GitHub Actions  

---

## Why we built it this way

| Choice | Why |
|---|---|
| Quiz profile, not “users like you” graphs | Works for first-time visitors |
| Strict filters | Budget / allergy-style exclusions must be trustworthy |
| Precomputed catalog files | Keeps the live site fast and cheap to host |
| Explanations need evidence | We only claim things we can back up |
| TF-IDF in production | Smaller and simpler than heavy embedding models |

---

## Does it work? (evaluation snapshot)

Full write-up: [BENCHMARK](docs/BENCHMARK.md).

| Situation | hit_rate@10 | Meaning |
|---|---:|---|
| Whole catalog | 1.1% | Hard test — many products, few “right” answers |
| Same category (more realistic) | **11.3%** | About **9×** better than “just pick popular” (1.3%) |

Takeaway: the system beats simple popularity when shopping inside a category. Absolute % on the full catalog looks small because the search space is large — that’s expected.

```bash
python -m pytest tests/ -q
```

---

## Test scenarios

Full list: [TEST_CASES](docs/TEST_CASES.md).

- **Automated in CI:** happy path, exclusions, category filter, validation errors, tiny budget  
- **Manual in the UI:** Why panel, placeholders, thin profiles, outdated product names  

| | What to try | What you should see |
|---|---|---|
| Happy path | Dry + hydration, $80 | Ranked list + reasons |
| Exclusion | Skip fragrance | No fragrance products |
| Stuck search | Budget $1 | “No match” + tips to relax filters |

---

## Limits & what’s next

**Honest limits today**

- No real product photos in the dataset → UI uses simple placeholders (exact-ID image enrichment is planned next)  
- “Similar shoppers” (cohort) only fires when a product has **≥ 5** reviews from that skin type — about **18.6%** of skin-type × product pairs qualify; the rest fall back to fit + reviews  
- Ingredient exclusions are keyword-based (not medical advice)  
- Catalog is a snapshot (prices/stock may change on Sephora.com)  

**Later ideas:** product images, routine builder (cleanser → serum → moisturizer), richer ranking with more data.

---

## Run locally

Need Python 3.12+ and Node 20+.

```bash
# Terminal 1 — API
pip install -r requirements-dev.txt
pip install -r backend/requirements.txt
python scripts/prepare_backend.py
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — website
cd frontend
npm install
npx next dev -p 3000
```

Open http://localhost:3000  

Curl / field reference: [API.md](docs/API.md) (includes `health` + `recommend` examples).

---

## Where this sits vs retail beauty apps

Same basic path as Nykaa/Sephora quizzes (questions → product grid). What’s different here is the **transparent scoring and evidence-backed “why”** on a fixed offline catalog — not live inventory, photos, or purchase-history personalization. Natural next steps are images and routines.

---

Data © brands / Sephora; dataset from nadyinky’s public release. Independent demo — not affiliated with Sephora, Nykaa, or Orbo beyond the assignment.
