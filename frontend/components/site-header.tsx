type SiteHeaderProps = {
  onHome?: () => void;
  showHome?: boolean;
};

export function SiteHeader({ onHome, showHome = false }: SiteHeaderProps) {
  return (
    <header className="border-b border-border bg-surface">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-2">
          <span className="text-xl font-bold tracking-tight text-accent">beauty</span>
          <span className="text-xl font-light tracking-tight text-foreground">recommender</span>
        </div>
        {showHome && onHome ? (
          <button type="button" onClick={onHome} className="text-sm font-medium text-body hover:text-accent">
            Home
          </button>
        ) : null}
      </div>
    </header>
  );
}
