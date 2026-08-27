import type { RecommendedProduct } from "@/lib/types";
import { formatPrice, formatScore } from "@/lib/constants";
import { ScoreBar } from "@/components/score-bar";

type WhyThisPanelProps = {
  product: RecommendedProduct | null;
};

export function WhyThisPanel({ product }: WhyThisPanelProps) {
  if (!product) {
    return (
      <aside className="rounded-sm border border-dashed border-border bg-surface p-6 text-center lg:sticky lg:top-4">
        <p className="text-sm font-medium text-foreground">Select a product</p>
        <p className="mt-2 text-sm text-muted">
          Click any card to see why it matched your profile.
        </p>
      </aside>
    );
  }

  const explanation = product.explanation;

  return (
    <aside className="rounded-sm border border-border bg-surface lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto">
      <div className="border-b border-border p-4">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">
          {product.brand}
        </p>
        <h3 className="mt-1 text-base font-semibold leading-snug text-foreground">
          {product.product_name}
        </h3>
        <div className="mt-3 flex items-baseline justify-between">
          <p className="text-2xl font-bold text-accent">{formatScore(product.scores.final_score)}</p>
          <p className="text-sm font-semibold text-foreground">{formatPrice(product.price_usd)}</p>
        </div>
      </div>

      <div className="space-y-5 p-4">
        {explanation && explanation.reasons.length > 0 ? (
          <section>
            <h4 className="mb-3 text-sm font-semibold text-foreground">Why this product</h4>
            <ul className="space-y-2">
              {explanation.reasons.map((reason) => (
                <li key={reason.claim_id} className="flex gap-2 text-sm leading-relaxed text-body">
                  <span className="shrink-0 font-bold text-accent">✓</span>
                  <span>{reason.message}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : (
          <p className="text-sm text-muted">Matched your profile based on our scoring model.</p>
        )}

        {explanation && explanation.components.length > 0 && (
          <section>
            <h4 className="mb-3 text-sm font-semibold text-foreground">Score breakdown</h4>
            <div className="space-y-3">
              {explanation.components.map((component) => (
                <ScoreBar key={component.key} label={component.label} rawScore={component.raw_score} />
              ))}
            </div>
          </section>
        )}
      </div>
    </aside>
  );
}
