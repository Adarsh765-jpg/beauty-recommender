export type SkinType = "combination" | "dry" | "normal" | "oily";

export type Concern =
  | "hydration"
  | "acne_oil_control"
  | "brightening"
  | "barrier_support"
  | "anti_aging";

export type Exclusion = "fragrance" | "drying_alcohol" | "paraben" | "sulfate";

export type RecommendRequest = {
  skin_type: SkinType;
  concerns: Concern[];
  exclusions: Exclusion[];
  budget_max_usd: number;
  category: string | null;
  top_k: number;
};

export type ScoreBreakdown = {
  skin_match: number;
  concern_match: number;
  text_similarity: number;
  content_score: number;
  cohort_score: number;
  quality_score: number;
  final_score: number;
  cohort_used: boolean;
};

export type ExplanationReason = {
  claim_id: string;
  message: string;
  evidence: string[];
};

export type ScoreComponent = {
  key: string;
  label: string;
  raw_score: number;
  weight: number;
  contribution: number;
};

export type Explanation = {
  final_score: number;
  cohort_used: boolean;
  reasons: ExplanationReason[];
  components: ScoreComponent[];
};

export type RecommendedProduct = {
  product_id: string;
  product_name: string;
  brand: string;
  price_usd: number;
  rating: number | null;
  review_count: number;
  secondary_category: string;
  tertiary_category: string;
  derived_concerns: string[];
  derived_benefits: string[];
  suited_skin_types: string[];
  scores: ScoreBreakdown;
  explanation: Explanation | null;
};

export type RecommendResponse = {
  status: "ok" | "no_match";
  profile: Record<string, unknown>;
  items: RecommendedProduct[];
  candidate_count: number;
  filtered_count: number;
  relaxations: string[];
};

export type BeautyProfileForm = {
  skinType: SkinType | null;
  concerns: Concern[];
  exclusions: Exclusion[];
  budgetMaxUsd: number;
  category: string | null;
};

export type ValidationErrorDetail = {
  field: string;
  message: string;
  type: string;
};

export type ApiError = {
  error: string;
  detail: string | ValidationErrorDetail[];
};
