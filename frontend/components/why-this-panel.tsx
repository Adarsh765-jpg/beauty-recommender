"use client";

import { useEffect, useId, useState } from "react";

import { ScoreBar } from "@/components/score-bar";
import { formatPrice, formatScore } from "@/lib/constants";
import { shopperReason } from "@/lib/sort";
import type { RecommendedProduct } from "@/lib/types";

type WhyThisPanelProps = {
  product: RecommendedProduct | null;
  skinType?: string | null;
  favorited?: boolean;
  onToggleFavorite?: () => void;
  onCloseMobile?: () => void;
  mobileOpen?: boolean;
};

export function WhyThisPanel({
  product,
  skinType,
  favorited = false,
  onToggleFavorite,
  onCloseMobile,
  mobileOpen = false,
}: WhyThisPanelProps) {
  const titleId = useId();

  useEffect(() => {
    if (!mobileOpen) return;

    const media = window.matchMedia("(max-width: 1023px)");
    if (!media.matches) return;

    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onChange = () => {
      if (!media.matches) {
        document.body.style.overflow = previous;
      }
    };
    media.addEventListener("change", onChange);

    return () => {
      media.removeEventListener("change", onChange);
      document.body.style.overflow = previous;
    };
  }, [mobileOpen]);

  const content = product ? (
    <PanelBody
      key={product.product_id}
      product={product}
      skinType={skinType}
      favorited={favorited}
      onToggleFavorite={onToggleFavorite}
      titleId={titleId}
    />
  ) : (
    <div className="p-6 text-center">
      <p className="font-display text-xl text-foreground">Why this pick?</p>
      <p className="mt-2 text-sm text-muted">
        Select a product to see clear, evidence-backed reasons it suits your skin.
      </p>
    </div>
  );

  return (
    <>
      <aside className="hidden rounded-[var(--radius-lg)] border border-border bg-surface-elevated shadow-[var(--shadow-sm)] lg:sticky lg:top-5 lg:block lg:max-h-[calc(100vh-2.5rem)] lg:overflow-y-auto">
        {content}
      </aside>

      {product && mobileOpen ? (
        <div className="lg:hidden">
          <button
            type="button"
            className="sheet-backdrop fixed inset-0 z-40"
            aria-label="Close product details"
            onClick={onCloseMobile}
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            className="animate-sheet-in fixed inset-x-0 bottom-0 z-50 max-h-[85vh] overflow-y-auto rounded-t-[1.5rem] border border-border bg-surface-elevated shadow-[var(--shadow-md)]"
          >
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-surface-elevated px-4 py-3">
              <div className="mx-auto h-1 w-10 rounded-full bg-border-strong" aria-hidden />
              <button type="button" className="btn-ghost absolute right-2 top-1.5" onClick={onCloseMobile}>
                Close
              </button>
            </div>
            {content}
          </div>
        </div>
      ) : null}
    </>
  );
}

function PanelBody({
  product,
  skinType,
  favorited,
  onToggleFavorite,
  titleId,
}: {
  product: RecommendedProduct;
  skinType?: string | null;
  favorited: boolean;
  onToggleFavorite?: () => void;
  titleId: string;
}) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const explanation = product.explanation;
  const category = product.tertiary_category || product.secondary_category;

  return (
    <div className="animate-fade-up">
      <div className="border-b border-border p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
              {product.brand}
            </p>
            <h3 id={titleId} className="font-display mt-1 text-2xl leading-snug text-foreground">
              {product.product_name}
            </h3>
            <p className="mt-2 text-xs text-muted">{category}</p>
          </div>
          {onToggleFavorite ? (
            <button
              type="button"
              onClick={onToggleFavorite}
              className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border transition ${
                favorited
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-border text-muted hover:border-accent hover:text-accent"
              }`}
              aria-label={favorited ? "Remove from saved" : "Save product"}
              aria-pressed={favorited}
            >
              <HeartIcon filled={favorited} />
            </button>
          ) : null}
        </div>

        <div className="mt-4 flex items-end justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">Match</p>
            <p className="font-display text-3xl text-accent">
              {formatScore(product.scores.final_score)}
            </p>
          </div>
          <p className="text-lg font-semibold text-foreground">{formatPrice(product.price_usd)}</p>
        </div>
      </div>

      <div className="space-y-5 p-5">
        <section>
          <h4 className="font-display text-xl text-foreground">Why this pick</h4>
          {explanation && explanation.reasons.length > 0 ? (
            <ul className="mt-3 space-y-3">
              {explanation.reasons.map((reason) => (
                <li key={reason.claim_id} className="flex gap-3 text-sm leading-relaxed text-body">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs text-accent">
                    ✓
                  </span>
                  <span>{shopperReason(reason, skinType)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-muted">
              This pick rose to the top based on how well it fits your skin profile and preferences.
            </p>
          )}
        </section>

        {explanation && explanation.components.length > 0 ? (
          <section>
            <button
              type="button"
              onClick={() => setDetailsOpen((current) => !current)}
              className="flex w-full items-center justify-between rounded-[var(--radius-sm)] border border-border bg-brown-soft/40 px-3 py-2.5 text-left text-sm font-medium text-foreground transition hover:bg-brown-soft"
              aria-expanded={detailsOpen}
            >
              <span>Score details</span>
              <span className="text-muted">{detailsOpen ? "Hide" : "Show"}</span>
            </button>
            {detailsOpen ? (
              <div className="mt-3 space-y-3 rounded-[var(--radius-sm)] border border-border p-3">
                {explanation.components.map((component) => (
                  <ScoreBar
                    key={component.key}
                    label={component.label}
                    rawScore={component.raw_score}
                  />
                ))}
              </div>
            ) : null}
          </section>
        ) : null}
      </div>
    </div>
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
