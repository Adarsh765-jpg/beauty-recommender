# Test cases

Representative scenarios for evaluators. Automated coverage: `tests/` (pytest).

## Successful scenarios

### S1 — Dry + hydration (happy path)

**Input**

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

**Expected**

- `status: "ok"`
- 5 ranked items, decreasing `final_score`
- Top products suited to dry skin and/or hydration concerns
- Each item has `explanation.reasons` and `explanation.components`

**How to try:** Quick demo or full quiz with Dry + Hydration, budget $80.

---

### S2 — Exclusions respected

**Input:** combination skin, fragrance exclusion, budget $100.

**Expected**

- No returned product has `exclusion_flags.fragrance == true`
- Still returns ranked products if enough catalog remains

---

### S3 — Category focus

**Input:** oily skin, category `"Moisturizers"`.

**Expected**

- Every item has secondary or tertiary category matching Moisturizers
- `candidate_count` smaller than unrestricted search

---

### S4 — Explainability panel

**Action:** Open results and select product #1.

**Expected**

- Why-this panel shows human-readable reasons (not raw `skin_match=1.0` dumps)
- Score bars for components that contributed to the final score

---

### S5 — Validation errors

**Input:** `"skin_type": "sensitive"` (unsupported).

**Expected**

- HTTP 422
- `error: "validation_error"` with field-level detail for `skin_type`

---

## Failure / limitation scenarios

### F1 — Budget too low

**Input:** `budget_max_usd: 1`

**Expected**

- `status: "no_match"`, empty `items`
- Non-empty `relaxations` suggesting a higher budget

**Why it struggles:** Almost no in-stock products under $1.

---

### F2 — Over-constrained filters

**Input:** narrow category + many exclusions + low budget.

**Expected**

- Often `no_match` or a very small candidate set
- System suggests relaxing exclusions/category/budget

---

### F3 — Missing product images

**Observation:** Cards show category placeholders, not photos.

**Why:** Source Sephora CSV has no image/SKU image fields. Not a ranking failure — a data gap.

---

### F4 — Weak text / concern signal

**Input:** skin type only, no concerns.

**Expected**

- Still returns products (skin + quality + cohort can dominate)
- Fewer concern-related explanation bullets

**Why imperfect:** Ranking leans on skin suitability and popularity proxies when goals are unspecified.

---

### F5 — Discontinued / renamed catalog items

**Observation:** Some high-ranked names may no longer match live Sephora pages.

**Why:** Static snapshot dataset; no live inventory sync.

---

## API field reminder

| Field | Meaning |
|---|---|
| `candidate_count` | Products that **passed** hard filters (eligible pool) |
| `filtered_count` | Products **rejected** by filters |

UI copy should refer to `candidate_count` when saying “matching your filters.”
