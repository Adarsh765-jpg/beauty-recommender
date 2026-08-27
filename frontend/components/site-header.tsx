type SiteHeaderProps = {
  onHome?: () => void;
  showHome?: boolean;
  savedCount?: number;
  onOpenSaved?: () => void;
};

export function SiteHeader({
  onHome,
  showHome = false,
  savedCount = 0,
  onOpenSaved,
}: SiteHeaderProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-border/80 bg-surface/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <button
          type="button"
          onClick={onHome}
          className="flex items-baseline gap-2 text-left"
          aria-label="Beauty recommender home"
        >
          <span className="font-display text-2xl tracking-tight text-brown">beauty</span>
          <span className="text-sm font-medium uppercase tracking-[0.22em] text-muted">
            recommender
          </span>
        </button>

        <div className="flex items-center gap-1 sm:gap-2">
          {onOpenSaved ? (
            <button type="button" onClick={onOpenSaved} className="btn-ghost">
              Saved{savedCount > 0 ? ` (${savedCount})` : ""}
            </button>
          ) : null}
          {showHome && onHome ? (
            <button type="button" onClick={onHome} className="btn-ghost">
              Home
            </button>
          ) : null}
        </div>
      </div>
    </header>
  );
}
