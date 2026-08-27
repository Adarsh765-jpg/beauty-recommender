import type { ApiError, RecommendRequest, RecommendResponse } from "@/lib/types";

export async function fetchRecommendations(
  payload: RecommendRequest,
): Promise<RecommendResponse> {
  const response = await fetch("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const body = (await response.json()) as RecommendResponse | ApiError;

  if (!response.ok) {
    const error = body as ApiError;
    if (error.error === "validation_error" && Array.isArray(error.detail)) {
      const messages = error.detail.map((item) => `${item.field}: ${item.message}`).join("; ");
      throw new Error(messages || "Invalid profile input.");
    }
    if (typeof error.detail === "string") {
      throw new Error(error.detail);
    }
    throw new Error("Could not load recommendations.");
  }

  return body as RecommendResponse;
}
