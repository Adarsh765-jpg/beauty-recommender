import type { RecommendedProduct } from "@/lib/types";

const STORAGE_KEY = "beauty-recommender:favorites:v1";

function readStore(): RecommendedProduct[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as RecommendedProduct[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeStore(items: RecommendedProduct[]) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

export function listFavorites(): RecommendedProduct[] {
  return readStore();
}

export function isFavorite(productId: string): boolean {
  return readStore().some((item) => item.product_id === productId);
}

export function toggleFavorite(product: RecommendedProduct): RecommendedProduct[] {
  const current = readStore();
  const exists = current.some((item) => item.product_id === product.product_id);
  const next = exists
    ? current.filter((item) => item.product_id !== product.product_id)
    : [product, ...current.filter((item) => item.product_id !== product.product_id)];
  writeStore(next);
  return next;
}

export function favoriteIds(items: RecommendedProduct[] = readStore()): Set<string> {
  return new Set(items.map((item) => item.product_id));
}
