# Sephora Dataset Audit

Generated: 2026-08-26T20:11:29.185807+00:00

## Source files

- **product_info.csv**: 7,904,227 bytes
- **skincare_products_reviews.csv**: 24,193,736 bytes

## Products

- Total products: **8,494**
- Skincare products (`primary_category == Skincare`): **2,420**
- Duplicate product IDs: **0**
- Missing ingredients: **11.13%**
- Missing highlights: **25.98%**

### Skincare price (USD)

- Median: $44.0
- p25–p75: $28.0 – $70.0
- p90: $110.0

## Reviews

- Review rows: **49,977**
- Unique reviewers: **38,907**
- Reviews per reviewer — median: **1.0**, mean: **1.285**, max: **35**
- Reviews per product — median: **33.0**, mean: **45.269**, max: **200**
- `is_recommended` present: **92.36%**
- Rating vs `is_recommended` agreement: **96.51%**

### Skin type distribution (normalized)

- `combination`: 25,172
- `dry`: 9,267
- `nan`: 3,631
- `normal`: 6,736
- `oily`: 5,171

- Observed skin types (excluding NaN): ['combination', 'dry', 'normal', 'oily']

## Join coverage

- Skincare products: **2,420**
- Skincare products with reviews in this file: **1,104**
- Skincare products without reviews in this file: **1,316**

## Product × skin_type cohort density

- Total product–skin_type cells: **3,895**
- Cell review count — median: **7.0**, max: **94**

### Threshold summary (cells meeting MIN_REVIEWS)

| MIN_REVIEWS | cells | % of cells | products with ≥1 qualifying cell |
|---|---:|---:|---:|
| 3 | 3,017 | 77.46% | 985 |
| 5 | 2,445 | 62.77% | 883 |
| 10 | 1,520 | 39.02% | 707 |
| 15 | 975 | 25.03% | 588 |
| 20 | 668 | 17.15% | 491 |

## Highlights skin-type signal (skincare only)

- Skincare rows with non-empty highlights: **2,003**
- Skincare rows with any skin keyword in highlights: **1,124**

### Skin keyword hits in highlights

- `normal skin`: 660
- `dryness`: 603
- `for dry`: 467
- `for oily`: 317
- `dry skin`: 95
- `oily skin`: 33
- `for normal`: 31
- `combination skin`: 21
- `for combination`: 21

## Spec number comparison

- `total_products_8494`: **MATCH**
- `skincare_products_2420`: **MATCH**
- `review_rows_49977`: **MATCH**
- `reviewed_skincare_1104`: **MATCH**
- `skincare_no_reviews_1316`: **MATCH**
- `is_recommended_present_pct_92_4`: **MATCH**
- `ingredients_missing_pct_11_1`: **MATCH**
- `highlights_missing_pct_26_0`: **MATCH**
- `median_reviews_per_reviewer_1`: **MATCH**
- `mean_reviews_per_reviewer_1_28`: **MATCH**
