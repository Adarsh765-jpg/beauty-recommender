"use client";

import type { RecommendedProduct } from "@/lib/types";
import { concernLabel, formatPrice, formatScore } from "@/lib/constants";

type ProductCardProps = {
  product: RecommendedProduct;
  rank: number;
  selected: boolean;
  favorited: boolean;
  onSelect: () => void;
  onToggleFavorite: () => void;
};

function AbstractPlaceholder({ label }: { label: string }) {
  return (
    <div className="placeholder-texture relative flex aspect-[4/5] w-full items-end justify-start overflow-hidden">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "linear-gradient(120deg, transparent 40%, rgb(255 252 249 / 55%) 50%, transparent 60%)",
        }}
        aria-hidden
      />
      <p className="relative m-3 rounded-full bg-surface/80 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.14em] text-muted backdrop-blur-sm">
        {label}
      </p>
    </div>
  );
}

export function ProductCard({
  product,
  rank,
  selected,
  favorited,
  onSelect,
  onToggleFavorite,
}: ProductCardProps) {
  const category = product.tertiary_category || product.secondary_category;
  const matchLabel = formatScore(product.scores.final_score);

  return (
    <article
      className={`group relative flex h-full flex-col overflow-hidden rounded-[var(--radius-md)] border bg-surface-elevated shadow-[var(--shadow-sm)] transition duration-200 ${
        selected
          ? "border-accent shadow-[var(--shadow-md)] ring-1 ring-accent/40"
          : "border-border hover:-translate-y-0.5 hover:shadow-[var(--shadow-md)]"
      }`}
    >
      <button
        type="button"
        onClick={onSelect}
        className="flex flex-1 flex-col text-left focus-visible:outline-none"
        aria-pressed={selected}
        aria-label={`${product.product_name} by ${product.brand}. ${matchLabel}. Open why this pick.`}
      >
        <div className="relative">
          <AbstractPlaceholder label={category} />
          <span className="absolute left-3 top-3 rounded-full bg-surface-elevated/95 px-2.5 py-1 text-[11px] font-semibold text-brown shadow-sm">
            #{rank}
          </span>
          <span className="absolute bottom-3 right-3 rounded-full bg-brown px-2.5 py-1 text-[11px] font-semibold text-white shadow-sm">
            {matchLabel}
          </span>
        </div>

        <div className="flex flex-1 flex-col gap-2 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            {product.brand}
          </p>
          <h3 className="font-display line-clamp-2 min-h-[2.75rem] text-lg leading-snug text-foreground">
            {product.product_name}
          </h3>

          <div className="mt-auto flex items-end justify-between gap-3 pt-2">
            <div>
              <p className="text-base font-semibold text-foreground">
                {formatPrice(product.price_usd)}
              </p>
              {product.rating !== null && product.review_count >= 5 ? (
                <p className="mt-0.5 text-xs text-muted">
                  <span className="font-medium text-rating">★ {product.rating.toFixed(1)}</span>
                  <span> ({product.review_count.toLocaleString()})</span>
                </p>
              ) : (
                <p className="mt-0.5 text-xs text-muted">New to reviews</p>
              )}
            </div>
            <span className="text-xs font-medium text-accent opacity-0 transition group-hover:opacity-100 group-focus-within:opacity-100">
              Why this →
            </span>
          </div>

          {product.derived_concerns.length > 0 ? (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {product.derived_concerns.slice(0, 2).map((concern) => (
                <span
                  key={concern}
                  className="rounded-full bg-brown-soft px-2 py-0.5 text-[11px] text-body"
                >
                  {concernLabel(concern)}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </button>

      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          onToggleFavorite();
        }}
        className={`absolute right-3 top-3 z-10 flex h-9 w-9 items-center justify-center rounded-full border bg-surface-elevated/95 shadow-sm transition ${
          favorited
            ? "border-accent text-accent"
            : "border-border text-muted hover:border-accent hover:text-accent"
        }`}
        aria-label={favorited ? "Remove from saved" : "Save product"}
        aria-pressed={favorited}
      >
        <HeartIcon filled={favorited} />
      </button>
    </article>
  );
}

function HeartIcon({ filled }: { filled: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
      <path
        d="M12 20s-7-4.35-7-9.2A3.8 3.8 0 0 1 12 8.2a3.8 3.8 0 0 1 7 2.6C19 15.65 12 20 12 20Z"
        fill={filled ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
    </svg>
  );
}
