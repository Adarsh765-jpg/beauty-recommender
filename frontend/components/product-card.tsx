import type { RecommendedProduct } from "@/lib/types";
import { concernLabel, formatPrice, formatScore } from "@/lib/constants";

type ProductCardProps = {
  product: RecommendedProduct;
  rank: number;
  selected: boolean;
  onSelect: () => void;
};

function ProductImagePlaceholder({ category }: { category: string }) {
  return (
    <div className="flex h-36 w-full items-center justify-center bg-[#fafafa]">
      <div className="text-center">
        <div className="mx-auto mb-2 flex h-14 w-14 items-center justify-center rounded-full bg-white shadow-sm">
          <svg
            viewBox="0 0 24 24"
            className="h-7 w-7 text-muted"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            aria-hidden
          >
            <path d="M8 4h8l1 2h3v2H4V6h3l1-2z" />
            <rect x="6" y="8" width="12" height="12" rx="2" />
          </svg>
        </div>
        <p className="text-[11px] text-muted">{category}</p>
      </div>
    </div>
  );
}

export function ProductCard({ product, rank, selected, onSelect }: ProductCardProps) {
  const category = product.tertiary_category || product.secondary_category;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`flex h-full w-full flex-col overflow-hidden rounded-sm bg-surface text-left transition-shadow ${
        selected
          ? "ring-2 ring-accent ring-offset-2 ring-offset-background"
          : "shadow-sm hover:shadow-md"
      }`}
    >
      <div className="relative">
        <ProductImagePlaceholder category={category} />
        <span className="absolute left-2 top-2 rounded-sm bg-surface px-1.5 py-0.5 text-[11px] font-semibold text-body shadow-sm">
          #{rank}
        </span>
        <span className="absolute right-2 top-2 rounded-sm bg-accent px-2 py-0.5 text-[11px] font-semibold text-white">
          {formatScore(product.scores.final_score)}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-1.5 p-3">
        <p className="truncate text-[11px] font-semibold uppercase tracking-wide text-muted">
          {product.brand}
        </p>
        <h3 className="line-clamp-2 min-h-[2.5rem] text-sm leading-snug text-foreground">
          {product.product_name}
        </h3>

        {product.rating !== null && product.review_count >= 5 ? (
          <p className="text-xs">
            <span className="font-semibold text-rating">★ {product.rating.toFixed(1)}</span>
            <span className="text-muted"> ({product.review_count.toLocaleString()})</span>
          </p>
        ) : (
          <p className="text-xs text-muted">No ratings yet</p>
        )}

        <p className="mt-auto pt-1 text-base font-semibold text-foreground">
          {formatPrice(product.price_usd)}
        </p>

        {product.derived_concerns.length > 0 && (
          <p className="truncate text-xs text-muted">
            {product.derived_concerns.slice(0, 2).map(concernLabel).join(" · ")}
          </p>
        )}
      </div>
    </button>
  );
}
