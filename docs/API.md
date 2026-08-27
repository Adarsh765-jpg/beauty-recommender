# API (simple guide)

The website talks to three endpoints. You can also call them yourself.

**Live:** https://beauty-recommender.vercel.app  
**Local:** http://127.0.0.1:8000  
**Interactive docs (when API is running):** `/api/docs`

---

## The three endpoints

| Call | URL | What it does |
|---|---|---|
| Check the API | `GET /api/health` | “Is it up? Are product files loaded?” |
| List allowed answers | `GET /api/schema` | Valid skin types, concerns, exclusions |
| Get recommendations | `POST /api/recommend` | Main quiz → ranked products |

---

## Ask for recommendations

Send JSON like this:

```json
{
  "skin_type": "dry",
  "concerns": ["hydration"],
  "exclusions": [],
  "budget_max_usd": 80,
  "category": null,
  "top_k": 5
}
```

| Field | Meaning |
|---|---|
| `skin_type` | `dry`, `oily`, `combination`, or `normal` |
| `concerns` | Goals like hydration, brightening, … |
| `exclusions` | Things to avoid (e.g. `fragrance`) |
| `budget_max_usd` | Max price |
| `category` | Optional focus (e.g. Moisturizers) |
| `top_k` | How many products to return (1–50) |

### What you get back

| Field | Meaning |
|---|---|
| `status` | `ok` or `no_match` |
| `items` | The ranked products, scores, and explanations |
| `candidate_count` | How many products passed the hard rules |
| `filtered_count` | How many were ruled out |
| `relaxations` | Tips if nothing matched (raise budget, etc.) |

---

## Try it in a terminal

```bash
curl http://127.0.0.1:8000/api/health

curl -X POST http://127.0.0.1:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d "{\"skin_type\":\"dry\",\"concerns\":[\"hydration\"],\"budget_max_usd\":80,\"top_k\":5}"
```

Bad skin type (e.g. `sensitive`) → error **422**.

More walkthroughs: [TEST_CASES](TEST_CASES.md).
