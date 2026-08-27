import type { ExplanationReason, RecommendedProduct } from "@/lib/types";
import { concernLabel, skinTypeLabel } from "@/lib/constants";

export type SortKey = "match" | "price_asc" | "price_desc" | "rating";

export function sortProducts(
  items: RecommendedProduct[],
  sortKey: SortKey,
): RecommendedProduct[] {
  const copy = [...items];
  copy.sort((a, b) => {
    switch (sortKey) {
      case "match":
        return b.scores.final_score - a.scores.final_score;
      case "price_asc":
        return a.price_usd - b.price_usd;
      case "price_desc":
        return b.price_usd - a.price_usd;
      case "rating": {
        const ratingA = a.rating ?? -1;
        const ratingB = b.rating ?? -1;
        if (ratingB !== ratingA) return ratingB - ratingA;
        return b.review_count - a.review_count;
      }
      default: {
        const _exhaustive: never = sortKey;
        return _exhaustive;
      }
    }
  });
  return copy;
}

/** Map backend claims into shopper-friendly copy without changing the API. */
export function shopperReason(reason: ExplanationReason, skinType?: string | null): string {
  if (reason.claim_id === "skin_suitability") {
    const skin = skinType ? skinTypeLabel(skinType).toLowerCase() : "your";
    return `Great fit for ${skin} skin`;
  }
  if (reason.claim_id.startsWith("concern_")) {
    const concern = reason.claim_id.replace("concern_", "");
    return `Targets your concern: ${concernLabel(concern).toLowerCase()}`;
  }
  if (reason.claim_id === "text_similarity") {
    return "Contains ingredients aligned with your preferences";
  }
  if (reason.claim_id === "cohort_prior") {
    return "Often liked by people with similar skin profiles";
  }
  if (reason.claim_id === "review_quality") {
    return reason.message.replace("Strong reviews", "Well reviewed by shoppers");
  }
  return reason.message;
}
