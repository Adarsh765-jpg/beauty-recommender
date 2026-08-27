import type { BeautyProfileForm, RecommendResponse } from "@/lib/types";
import type { SortKey } from "@/lib/sort";

const STORAGE_KEY = "beauty-recommender:session:v1";

export type AppPhase = "landing" | "onboarding" | "loading" | "results";
export type ResultsTab = "recommended" | "saved";

export type SessionSnapshot = {
  phase: Exclude<AppPhase, "loading">;
  step: number;
  form: BeautyProfileForm;
  results: RecommendResponse | null;
  selectedId: string | null;
  sortKey: SortKey;
  resultsTab: ResultsTab;
  topK: number;
};

export function readSession(): SessionSnapshot | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as SessionSnapshot;
    if (!parsed || !parsed.phase || !parsed.form) return null;
    if (parsed.phase === "landing") return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writeSession(snapshot: SessionSnapshot) {
  if (typeof window === "undefined") return;
  if (snapshot.phase === "landing") {
    window.sessionStorage.removeItem(STORAGE_KEY);
    return;
  }
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
}

export function clearSession() {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(STORAGE_KEY);
}
