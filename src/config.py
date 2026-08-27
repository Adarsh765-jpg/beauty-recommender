"""Shared configuration for offline data and artifact paths."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
DATA_SAMPLE = PROJECT_ROOT / "data" / "sample"
DATA_AUDIT = PROJECT_ROOT / "data" / "audit"
DATA_ARTIFACTS = PROJECT_ROOT / "data" / "artifacts"

PRODUCT_INFO_FILENAME = "product_info.csv"
REVIEWS_FILENAME = "skincare_products_reviews.csv"

GITHUB_BASE_URL = "https://raw.githubusercontent.com/nadyinky/sephora-analysis/main/datasets"

SKINCARE_PRIMARY_CATEGORY = "Skincare"

SKIN_TYPES = ("combination", "dry", "normal", "oily")

# Skin-type cohort prior gate (chosen in Phase 1 audit).
COHORT_MIN_REVIEWS = 5

# Candidate thresholds recorded in the audit report.
COHORT_MIN_REVIEWS_CANDIDATES = (3, 5, 10, 15, 20)

# User-facing concern goals supported by the feature layer and UI.
CONCERNS = (
    "hydration",
    "acne_oil_control",
    "brightening",
    "barrier_support",
    "anti_aging",
)

# Ingredient / highlight keyword -> concern mapping.
INGREDIENT_CONCERN_RULES: tuple[tuple[str, str], ...] = (
    ("hyaluronic acid", "hydration"),
    ("sodium hyaluronate", "hydration"),
    ("glycerin", "hydration"),
    ("ceramide", "barrier_support"),
    ("ceramides", "barrier_support"),
    ("salicylic acid", "acne_oil_control"),
    ("benzoyl peroxide", "acne_oil_control"),
    ("retinol", "anti_aging"),
    ("retinal", "anti_aging"),
    ("bakuchiol", "anti_aging"),
    ("ascorbic acid", "brightening"),
    ("vitamin c", "brightening"),
    ("niacinamide", "brightening"),
    ("azelaic acid", "brightening"),
    ("alpha arbutin", "brightening"),
    ("tranexamic acid", "brightening"),
)

HIGHLIGHT_CONCERN_RULES: tuple[tuple[str, str], ...] = (
    ("dryness", "hydration"),
    ("hydration", "hydration"),
    ("moisture", "hydration"),
    ("acne", "acne_oil_control"),
    ("blemish", "acne_oil_control"),
    ("oiliness", "acne_oil_control"),
    ("pores", "acne_oil_control"),
    ("brightening", "brightening"),
    ("dark spot", "brightening"),
    ("uneven tone", "brightening"),
    ("dullness", "brightening"),
    ("redness", "barrier_support"),
    ("barrier", "barrier_support"),
    ("fine lines", "anti_aging"),
    ("wrinkle", "anti_aging"),
    ("anti-aging", "anti_aging"),
)

# Vocabulary used to validate concern rules against review text (Phase 3c).
CONCERN_REVIEW_VOCAB: dict[str, tuple[str, ...]] = {
    "hydration": ("hydration", "hydrating", "moisture", "moisturizing", "dry", "dryness"),
    "acne_oil_control": ("acne", "breakout", "oil", "oily", "pore", "blemish"),
    "brightening": ("bright", "brightening", "glow", "radiance", "dark spot", "hyperpigmentation"),
    "barrier_support": ("barrier", "redness", "irritation", "sensitive", "soothing"),
    "anti_aging": ("wrinkle", "fine line", "anti-aging", "firming", "aging"),
}

# Exclusion detection patterns applied to ingredient tokens (case-insensitive substring).
EXCLUSION_RULES: dict[str, tuple[str, ...]] = {
    "fragrance": ("fragrance", "parfum", "perfume"),
    "drying_alcohol": (
        "alcohol denat",
        "sd alcohol",
        "denatured alcohol",
        "isopropyl alcohol",
        "ethanol",
    ),
    "paraben": ("paraben",),
    "sulfate": ("sodium lauryl sulfate", "sodium laureth sulfate", "sls"),
}

# Content-score weights (tuned on validation split in Phase 6).
W_SKIN = 0.34
W_CONCERN = 0.34
W_TEXT = 0.32

# Final-score mixing weights (validated on val; Phase 8).
# Grid best was alpha=0.50, beta=0.35, gamma=0.15 (hit_rate@10 0.020 vs 0.011 here).
# Kept the conservative 0.60/0.25/0.15 mix to avoid chasing sparse val noise.
ALPHA = 0.60
BETA = 0.25
GAMMA = 0.15

# Diversity caps when selecting the displayed top-k from the ranked pool.
MAX_RESULTS_PER_BRAND = 2
MAX_RESULTS_PER_CATEGORY = 3

# UI category labels → catalog secondary/tertiary names (lowercase).
CATEGORY_ALIASES: dict[str, frozenset[str]] = {
    "moisturizers": frozenset({"moisturizers"}),
    "face serums": frozenset({"face serums"}),
    "cleansers": frozenset({"cleansers", "face wash & cleansers"}),
    "toners": frozenset({"toners", "mists & essences"}),
    "sunscreen": frozenset({"sunscreen", "face sunscreen"}),
    "eye creams & treatments": frozenset({"eye creams & treatments", "eye care"}),
    "face masks": frozenset({"face masks", "masks"}),
    "face oils": frozenset({"face oils"}),
    "treatments": frozenset(
        {
            "treatments",
            "facial peels",
            "exfoliators",
            "blemish & acne treatments",
        }
    ),
}

# Bayesian shrinkage for quality_score: pull sparse ratings toward catalog mean.
QUALITY_PRIOR_REVIEWS = 50

# Bayesian shrinkage for cohort prior toward global train recommendation rate.
COHORT_PRIOR_REVIEWS = 10

# Neutral skin-match score when a product has no derived skin suitability.
SKIN_MATCH_NEUTRAL = 0.5

# TF-IDF settings shared by offline sklearn fit and runtime numpy transform.
TFIDF_NORM = "l2"
TFIDF_USE_IDF = True
TFIDF_SMOOTH_IDF = True
TFIDF_SUBLINEAR_TF = False

# Maximum total artifact payload budget for deployment (bytes).
ARTIFACT_SIZE_BUDGET_BYTES = 100 * 1024 * 1024

# Evaluation harness settings (Phase 5).
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_SMOKE_DIR = REPORTS_DIR / "smoke"
EVAL_TRAIN_RATIO = 0.70
EVAL_VAL_RATIO = 0.15
EVAL_TOP_K = (5, 10, 20)
EVAL_DEFAULT_BUDGET_USD = 9999.0
