"use client";

import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import { ProductCard } from "@/components/product-card";
import { SiteHeader } from "@/components/site-header";
import { WhyThisPanel } from "@/components/why-this-panel";
import { fetchRecommendations } from "@/lib/api";
import {
  BUDGET_PRESETS,
  CATEGORY_OPTIONS,
  CONCERN_OPTIONS,
  EXCLUSION_OPTIONS,
  ONBOARDING_STEPS,
  SKIN_TYPE_OPTIONS,
  concernLabel,
  exclusionLabel,
  formatPrice,
  skinTypeLabel,
} from "@/lib/constants";
import {
  favoriteIds,
  listFavorites,
  toggleFavorite,
} from "@/lib/favorites";
import {
  clearSession,
  readSession,
  writeSession,
  type AppPhase,
  type ResultsTab,
} from "@/lib/session";
import { sortProducts, type SortKey } from "@/lib/sort";
import type {
  BeautyProfileForm,
  Concern,
  Exclusion,
  RecommendedProduct,
  RecommendResponse,
} from "@/lib/types";

const INITIAL_FORM: BeautyProfileForm = {
  skinType: null,
  concerns: [],
  exclusions: [],
  budgetMaxUsd: 75,
  category: null,
};

const INITIAL_TOP_K = 10;
const TOP_K_STEP = 10;
const TOP_K_MAX = 50;
const BUDGET_STEPS = [30, 50, 75, 100, 150, 9999] as const;

const SORT_OPTIONS: { id: SortKey; label: string }[] = [
  { id: "match", label: "Best match" },
  { id: "price_asc", label: "Price ↑" },
  { id: "price_desc", label: "Price ↓" },
  { id: "rating", label: "Top rated" },
];

function nextBudget(current: number): number {
  for (const step of BUDGET_STEPS) {
    if (step > current) return step;
  }
  return 9999;
}

export function BeautyApp() {
  const [phase, setPhase] = useState<AppPhase>("landing");
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<BeautyProfileForm>(INITIAL_FORM);
  const [results, setResults] = useState<RecommendResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [favorites, setFavorites] = useState<RecommendedProduct[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>("match");
  const [resultsTab, setResultsTab] = useState<ResultsTab>("recommended");
  const [mobileSheetOpen, setMobileSheetOpen] = useState(false);
  const [topK, setTopK] = useState(INITIAL_TOP_K);
  const [loadingMore, setLoadingMore] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);

  useEffect(() => {
    // Client-only hydrate from storage after SSR (localStorage/sessionStorage).
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional post-hydration restore
    setFavorites(listFavorites());
    const saved = readSession();
    if (saved) {
      setPhase(saved.phase);
      setStep(saved.step);
      setForm(saved.form);
      setResults(saved.results);
      setSelectedId(saved.selectedId);
      setSortKey(saved.sortKey);
      setResultsTab(saved.resultsTab);
      setTopK(saved.topK);
    }
    setSessionReady(true);
  }, []);

  useEffect(() => {
    if (!sessionReady) return;
    if (phase === "loading") return;
    writeSession({
      phase,
      step,
      form,
      results,
      selectedId,
      sortKey,
      resultsTab,
      topK,
    });
  }, [sessionReady, phase, step, form, results, selectedId, sortKey, resultsTab, topK]);

  useEffect(() => {
    // Clear a leftover body scroll lock when entering results (desktop safety).
    if (phase === "results") {
      document.body.style.overflow = "";
    }
  }, [phase]);

  const favoritedSet = useMemo(() => favoriteIds(favorites), [favorites]);

  const selectedProduct = useMemo(() => {
    const fromResults = results?.items.find((item) => item.product_id === selectedId);
    if (fromResults) return fromResults;
    return favorites.find((item) => item.product_id === selectedId) ?? null;
  }, [results, selectedId, favorites]);

  function toggleConcern(concern: Concern) {
    setForm((current) => ({
      ...current,
      concerns: current.concerns.includes(concern)
        ? current.concerns.filter((item) => item !== concern)
        : [...current.concerns, concern],
    }));
  }

  function toggleExclusion(exclusion: Exclusion) {
    setForm((current) => ({
      ...current,
      exclusions: current.exclusions.includes(exclusion)
        ? current.exclusions.filter((item) => item !== exclusion)
        : [...current.exclusions, exclusion],
    }));
  }

  function canAdvance(): boolean {
    if (step === 0) return form.skinType !== null;
    return true;
  }

  async function submitProfile(override?: BeautyProfileForm) {
    const active = override ?? form;
    if (!active.skinType) return;
    if (override) {
      setForm(override);
    }

    setPhase("loading");
    setError(null);
    setResults(null);
    setSelectedId(null);
    setMobileSheetOpen(false);
    setResultsTab("recommended");
    setTopK(INITIAL_TOP_K);
    setLoadingMore(false);

    try {
      const response = await fetchRecommendations({
        skin_type: active.skinType,
        concerns: active.concerns,
        exclusions: active.exclusions,
        budget_max_usd: active.budgetMaxUsd,
        category: active.category,
        top_k: INITIAL_TOP_K,
      });
      setResults(response);
      if (response.items.length > 0) {
        setSelectedId(response.items[0].product_id);
        setMobileSheetOpen(false);
      }
      setPhase("results");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Something went wrong.");
      setPhase("results");
    }
  }

  async function showMoreRecommendations() {
    if (!form.skinType || loadingMore || !results) return;
    const nextTopK = Math.min(TOP_K_MAX, topK + TOP_K_STEP);
    if (nextTopK <= topK) return;
    if (results.items.length >= results.candidate_count) return;

    setLoadingMore(true);
    setError(null);
    try {
      const response = await fetchRecommendations({
        skin_type: form.skinType,
        concerns: form.concerns,
        exclusions: form.exclusions,
        budget_max_usd: form.budgetMaxUsd,
        category: form.category,
        top_k: nextTopK,
      });
      setResults(response);
      setTopK(nextTopK);
      if (!selectedId && response.items.length > 0) {
        setSelectedId(response.items[0].product_id);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Something went wrong.");
    } finally {
      setLoadingMore(false);
    }
  }

  function restart() {
    clearSession();
    setPhase("landing");
    setStep(0);
    setForm(INITIAL_FORM);
    setResults(null);
    setSelectedId(null);
    setError(null);
    setResultsTab("recommended");
    setMobileSheetOpen(false);
    setSortKey("match");
    setTopK(INITIAL_TOP_K);
    setLoadingMore(false);
  }

  function handleToggleFavorite(product: RecommendedProduct) {
    setFavorites(toggleFavorite(product));
  }

  function handleSelectProduct(product: RecommendedProduct) {
    setSelectedId(product.product_id);
    // Bottom sheet is mobile-only; opening it on desktop locked page scroll
    // while the sheet stayed hidden via lg:hidden.
    const isMobile = window.matchMedia("(max-width: 1023px)").matches;
    setMobileSheetOpen(isMobile);
  }

  if (!sessionReady) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent-muted border-t-accent" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader
        showHome={phase !== "landing"}
        onHome={restart}
        savedCount={favorites.length}
        onOpenSaved={
          phase === "results"
            ? () => {
                setResultsTab("saved");
                if (favorites[0]) {
                  setSelectedId(favorites[0].product_id);
                }
              }
            : undefined
        }
      />

      {phase === "landing" && (
        <main className="relative overflow-hidden">
          <div
            className="pointer-events-none absolute inset-0 opacity-70"
            style={{
              background:
                "radial-gradient(ellipse at top right, rgb(196 123 130 / 18%), transparent 45%), radial-gradient(ellipse at bottom left, rgb(58 46 39 / 6%), transparent 40%)",
            }}
            aria-hidden
          />
          <div className="relative mx-auto flex min-h-[calc(100vh-4rem)] max-w-5xl flex-col justify-center px-4 py-16 sm:px-6 sm:py-24">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted">
              Personalized skincare
            </p>
            <h1 className="font-display mt-4 max-w-3xl text-5xl leading-[1.05] text-foreground sm:text-6xl">
              Skincare, chosen with care for your skin.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-body sm:text-lg">
              A short ritual of questions. Curated Sephora picks. Clear reasons for every
              recommendation — so you know why it belongs in your routine.
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => {
                  setPhase("onboarding");
                  setStep(0);
                }}
                className="btn-primary"
              >
                Take the Quiz
              </button>
              <button
                type="button"
                onClick={() => {
                  setForm((current) => ({
                    ...current,
                    skinType: "combination",
                    concerns: ["brightening"],
                  }));
                  setPhase("onboarding");
                  setStep(4);
                }}
                className="btn-secondary"
              >
                Quick Demo
              </button>
            </div>
          </div>
        </main>
      )}

      {phase === "onboarding" && (
        <main className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-muted">
            Step {step + 1} of {ONBOARDING_STEPS.length} · {ONBOARDING_STEPS[step]}
          </p>
          <div className="mb-8 flex gap-1.5">
            {ONBOARDING_STEPS.map((label, index) => (
              <div
                key={label}
                className={`h-1 flex-1 rounded-full ${index <= step ? "bg-accent" : "bg-border"}`}
              />
            ))}
          </div>

          <div className="rounded-[var(--radius-lg)] border border-border bg-surface-elevated p-6 shadow-[var(--shadow-sm)] sm:p-8">
            {step === 0 && (
              <StepShell title="What's your skin type?" subtitle="We'll match products suited to your skin.">
                <div className="grid gap-3 sm:grid-cols-2">
                  {SKIN_TYPE_OPTIONS.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      onClick={() => setForm((current) => ({ ...current, skinType: option.id }))}
                      className={`rounded-[var(--radius-md)] border p-4 text-left transition ${
                        form.skinType === option.id
                          ? "border-accent bg-accent-soft"
                          : "border-border hover:border-border-strong hover:bg-brown-soft/30"
                      }`}
                    >
                      <p className="font-medium text-foreground">{option.label}</p>
                      <p className="mt-1 text-sm text-body">{option.hint}</p>
                    </button>
                  ))}
                </div>
              </StepShell>
            )}

            {step === 1 && (
              <StepShell title="What are your skin goals?" subtitle="Pick all that apply.">
                <ChipGrid
                  options={CONCERN_OPTIONS}
                  selected={form.concerns}
                  onToggle={(id) => toggleConcern(id as Concern)}
                />
              </StepShell>
            )}

            {step === 2 && (
              <StepShell title="Any ingredients to avoid?" subtitle="Optional — we'll filter these out.">
                <ChipGrid
                  options={EXCLUSION_OPTIONS}
                  selected={form.exclusions}
                  onToggle={(id) => toggleExclusion(id as Exclusion)}
                />
              </StepShell>
            )}

            {step === 3 && (
              <StepShell title="Budget & category" subtitle="Optional filters.">
                <div className="space-y-6">
                  <div>
                    <p className="mb-3 text-sm font-medium text-foreground">Max budget</p>
                    <div className="flex flex-wrap gap-2">
                      {BUDGET_PRESETS.map((preset) => (
                        <button
                          key={preset.value}
                          type="button"
                          onClick={() =>
                            setForm((current) => ({ ...current, budgetMaxUsd: preset.value }))
                          }
                          className={`chip ${form.budgetMaxUsd === preset.value ? "chip-selected" : "chip-default"}`}
                        >
                          {preset.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mb-3 text-sm font-medium text-foreground">Category</p>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => setForm((current) => ({ ...current, category: null }))}
                        className={`chip ${form.category === null ? "chip-selected" : "chip-default"}`}
                      >
                        All
                      </button>
                      {CATEGORY_OPTIONS.map((category) => (
                        <button
                          key={category}
                          type="button"
                          onClick={() => setForm((current) => ({ ...current, category }))}
                          className={`chip ${form.category === category ? "chip-selected" : "chip-default"}`}
                        >
                          {category}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </StepShell>
            )}

            {step === 4 && (
              <StepShell title="Review" subtitle="Ready to see your picks?">
                <dl className="divide-y divide-border text-sm">
                  <ReviewRow label="Skin type" value={form.skinType ? skinTypeLabel(form.skinType) : "—"} />
                  <ReviewRow
                    label="Goals"
                    value={
                      form.concerns.length > 0
                        ? form.concerns.map(concernLabel).join(", ")
                        : "None"
                    }
                  />
                  <ReviewRow
                    label="Avoid"
                    value={
                      form.exclusions.length > 0
                        ? form.exclusions.map(exclusionLabel).join(", ")
                        : "None"
                    }
                  />
                  <ReviewRow label="Budget" value={formatPrice(form.budgetMaxUsd)} />
                  <ReviewRow label="Category" value={form.category ?? "All"} />
                </dl>
              </StepShell>
            )}

            <div className="mt-8 flex justify-between gap-3 border-t border-border pt-6">
              <button
                type="button"
                onClick={() => setStep((current) => Math.max(0, current - 1))}
                disabled={step === 0}
                className="btn-secondary py-2.5"
              >
                Back
              </button>
              {step < ONBOARDING_STEPS.length - 1 ? (
                <button
                  type="button"
                  onClick={() => setStep((current) => current + 1)}
                  disabled={!canAdvance()}
                  className="btn-primary py-2.5"
                >
                  Continue
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => void submitProfile()}
                  disabled={!canAdvance()}
                  className="btn-primary py-2.5"
                >
                  Show my picks
                </button>
              )}
            </div>
          </div>
        </main>
      )}

      {phase === "loading" && (
        <main className="flex min-h-[50vh] flex-col items-center justify-center px-4 py-20 text-center">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-accent-muted border-t-accent" />
          <p className="font-display mt-6 text-2xl text-foreground">Curating your matches…</p>
          <p className="mt-2 text-sm text-muted">Matching products to your skin profile</p>
        </main>
      )}

      {phase === "results" && (
        <ResultsView
          form={form}
          results={results}
          error={error}
          selectedProduct={selectedProduct}
          favorites={favorites}
          favoritedSet={favoritedSet}
          sortKey={sortKey}
          resultsTab={resultsTab}
          mobileSheetOpen={mobileSheetOpen}
          onSortChange={setSortKey}
          onTabChange={setResultsTab}
          onSelect={(product) => handleSelectProduct(product)}
          onToggleFavorite={handleToggleFavorite}
          onCloseMobileSheet={() => setMobileSheetOpen(false)}
          onRestart={restart}
          onEditProfile={() => {
            setPhase("onboarding");
            setStep(4);
            setError(null);
          }}
          onUpdateFilters={(next) => void submitProfile(next)}
          onRaiseBudget={() =>
            void submitProfile({ ...form, budgetMaxUsd: nextBudget(form.budgetMaxUsd) })
          }
          onClearExclusions={() => void submitProfile({ ...form, exclusions: [] })}
          onClearCategory={() => void submitProfile({ ...form, category: null })}
          loadingMore={loadingMore}
          canShowMore={
            resultsTab === "recommended" &&
            !!results &&
            results.items.length > 0 &&
            results.items.length < Math.min(TOP_K_MAX, results.candidate_count) &&
            topK < TOP_K_MAX
          }
          onShowMore={() => void showMoreRecommendations()}
        />
      )}
    </div>
  );
}

function StepShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div>
      <h2 className="font-display text-3xl text-foreground">{title}</h2>
      <p className="mt-2 text-sm text-body">{subtitle}</p>
      <div className="mt-6">{children}</div>
    </div>
  );
}

function ChipGrid<T extends string>({
  options,
  selected,
  onToggle,
}: {
  options: { id: T; label: string }[];
  selected: T[];
  onToggle: (id: T) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          onClick={() => onToggle(option.id)}
          className={`chip ${selected.includes(option.id) ? "chip-selected" : "chip-default"}`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 py-3">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right font-medium text-foreground">{value}</dd>
    </div>
  );
}

function ResultsView({
  form,
  results,
  error,
  selectedProduct,
  favorites,
  favoritedSet,
  sortKey,
  resultsTab,
  mobileSheetOpen,
  onSortChange,
  onTabChange,
  onSelect,
  onToggleFavorite,
  onCloseMobileSheet,
  onRestart,
  onEditProfile,
  onUpdateFilters,
  onRaiseBudget,
  onClearExclusions,
  onClearCategory,
  loadingMore,
  canShowMore,
  onShowMore,
}: {
  form: BeautyProfileForm;
  results: RecommendResponse | null;
  error: string | null;
  selectedProduct: RecommendedProduct | null;
  favorites: RecommendedProduct[];
  favoritedSet: Set<string>;
  sortKey: SortKey;
  resultsTab: ResultsTab;
  mobileSheetOpen: boolean;
  onSortChange: (key: SortKey) => void;
  onTabChange: (tab: ResultsTab) => void;
  onSelect: (product: RecommendedProduct) => void;
  onToggleFavorite: (product: RecommendedProduct) => void;
  onCloseMobileSheet: () => void;
  onRestart: () => void;
  onEditProfile: () => void;
  onUpdateFilters: (form: BeautyProfileForm) => void;
  onRaiseBudget: () => void;
  onClearExclusions: () => void;
  onClearCategory: () => void;
  loadingMore: boolean;
  canShowMore: boolean;
  onShowMore: () => void;
}) {
  if (error) {
    return (
      <main className="mx-auto max-w-lg px-4 py-16 text-center sm:px-6">
        <h2 className="font-display text-3xl text-foreground">Couldn&apos;t load recommendations</h2>
        <p className="mt-2 text-sm text-body">{error}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <button type="button" onClick={onEditProfile} className="btn-primary py-2.5">
            Edit profile
          </button>
          <button type="button" onClick={onRestart} className="btn-secondary py-2.5">
            Start over
          </button>
        </div>
      </main>
    );
  }

  const noMatch =
    resultsTab === "recommended" &&
    (!results || results.status === "no_match" || results.items.length === 0);

  if (noMatch) {
    const raisedBudget = nextBudget(form.budgetMaxUsd);
    return (
      <main className="mx-auto max-w-lg px-4 py-16 text-center sm:px-6">
        <h2 className="font-display text-3xl text-foreground">Nothing matches all your filters</h2>
        <p className="mt-2 text-sm text-body">
          Try loosening one preference — we&apos;ll refresh your picks instantly.
        </p>
        <div className="mt-6 flex flex-col gap-2">
          {form.budgetMaxUsd < 9999 ? (
            <button type="button" onClick={onRaiseBudget} className="btn-primary w-full py-2.5">
              Increase budget to {formatPrice(raisedBudget)}
            </button>
          ) : null}
          {form.exclusions.length > 0 ? (
            <button type="button" onClick={onClearExclusions} className="btn-secondary w-full py-2.5">
              Remove ingredient exclusions
            </button>
          ) : null}
          {form.category ? (
            <button type="button" onClick={onClearCategory} className="btn-secondary w-full py-2.5">
              Expand categories
            </button>
          ) : null}
        </div>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <button type="button" onClick={onEditProfile} className="btn-secondary py-2.5">
            Edit profile
          </button>
          <button type="button" onClick={onRestart} className="btn-secondary py-2.5">
            Start over
          </button>
        </div>
      </main>
    );
  }

  const displayItems =
    resultsTab === "saved"
      ? sortProducts(favorites, sortKey)
      : sortProducts(results?.items ?? [], sortKey);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:py-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-3xl text-foreground sm:text-4xl">
            {resultsTab === "saved"
              ? `Saved${favorites.length ? ` · ${favorites.length}` : ""}`
              : `${displayItems.length} picks for ${form.skinType ? skinTypeLabel(form.skinType).toLowerCase() : "you"}`}
          </h2>
          <p className="mt-1 text-sm text-muted">
            {resultsTab === "saved"
              ? "Favorites stay saved even when your filters change."
              : `From ${(results?.candidate_count ?? 0).toLocaleString()} products matching your filters`}
          </p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={onEditProfile} className="btn-secondary py-2 text-sm">
            Edit profile
          </button>
          <button type="button" onClick={onRestart} className="btn-ghost py-2 text-sm">
            Restart
          </button>
        </div>
      </div>

      <ProfileSummary form={form} />

      <div className="mt-5 space-y-4 rounded-[var(--radius-lg)] border border-border bg-surface-elevated p-4 shadow-[var(--shadow-sm)] sm:p-5">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => onTabChange("recommended")}
            className={`chip ${resultsTab === "recommended" ? "chip-selected" : "chip-default"}`}
          >
            Recommended
          </button>
          <button
            type="button"
            onClick={() => onTabChange("saved")}
            className={`chip ${resultsTab === "saved" ? "chip-selected" : "chip-default"}`}
          >
            Saved ({favorites.length})
          </button>
          <div className="ml-auto flex flex-wrap gap-2">
            <label className="sr-only" htmlFor="sort-select">
              Sort products
            </label>
            <select
              id="sort-select"
              value={sortKey}
              onChange={(event) => onSortChange(event.target.value as SortKey)}
              className="rounded-full border border-border bg-surface px-3 py-1.5 text-sm text-foreground"
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {resultsTab === "recommended" ? (
          <ResultsFilters form={form} onUpdateFilters={onUpdateFilters} />
        ) : null}
      </div>

      {displayItems.length === 0 && resultsTab === "saved" ? (
        <div className="mt-10 rounded-[var(--radius-lg)] border border-dashed border-border bg-surface px-6 py-14 text-center">
          <p className="font-display text-2xl text-foreground">No saved products yet</p>
          <p className="mt-2 text-sm text-muted">Tap the heart on any card to save it here.</p>
          <button
            type="button"
            className="btn-primary mt-6"
            onClick={() => onTabChange("recommended")}
          >
            Back to recommendations
          </button>
        </div>
      ) : (
        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px] lg:items-start">
          <div>
            <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-3">
              {displayItems.map((product, index) => (
                <ProductCard
                  key={product.product_id}
                  product={product}
                  rank={index + 1}
                  selected={selectedProduct?.product_id === product.product_id}
                  favorited={favoritedSet.has(product.product_id)}
                  onSelect={() => onSelect(product)}
                  onToggleFavorite={() => onToggleFavorite(product)}
                />
              ))}
            </div>

            {resultsTab === "recommended" && canShowMore ? (
              <div className="mt-8 flex flex-col items-center gap-2">
                <button
                  type="button"
                  onClick={onShowMore}
                  disabled={loadingMore}
                  className="btn-secondary"
                >
                  {loadingMore ? "Loading more…" : "Show 10 more"}
                </button>
                <p className="text-xs text-muted">
                  Showing {displayItems.length} of{" "}
                  {Math.min(TOP_K_MAX, results?.candidate_count ?? displayItems.length)} curated
                  picks
                </p>
              </div>
            ) : null}

            {resultsTab === "recommended" &&
            results &&
            !canShowMore &&
            results.items.length > INITIAL_TOP_K ? (
              <p className="mt-8 text-center text-xs text-muted">
                Showing all {results.items.length} available picks for this profile
              </p>
            ) : null}
          </div>

          <WhyThisPanel
            product={selectedProduct}
            skinType={form.skinType}
            favorited={
              selectedProduct ? favoritedSet.has(selectedProduct.product_id) : false
            }
            onToggleFavorite={
              selectedProduct ? () => onToggleFavorite(selectedProduct) : undefined
            }
            mobileOpen={mobileSheetOpen}
            onCloseMobile={onCloseMobileSheet}
          />
        </div>
      )}
    </main>
  );
}

function ProfileSummary({ form }: { form: BeautyProfileForm }) {
  return (
    <section
      aria-label="Your beauty profile"
      className="flex flex-wrap gap-2 rounded-[var(--radius-md)] border border-border bg-brown-soft/35 px-3 py-3"
    >
      {form.skinType ? (
        <span className="rounded-full bg-surface px-3 py-1 text-xs font-medium text-foreground">
          {skinTypeLabel(form.skinType)} skin
        </span>
      ) : null}
      {form.concerns.map((concern) => (
        <span
          key={concern}
          className="rounded-full bg-surface px-3 py-1 text-xs font-medium text-foreground"
        >
          {concernLabel(concern)}
        </span>
      ))}
      <span className="rounded-full bg-surface px-3 py-1 text-xs font-medium text-foreground">
        {formatPrice(form.budgetMaxUsd)}
      </span>
      {form.exclusions.map((exclusion) => (
        <span
          key={exclusion}
          className="rounded-full bg-surface px-3 py-1 text-xs font-medium text-foreground"
        >
          {exclusionLabel(exclusion)}
        </span>
      ))}
      {form.category ? (
        <span className="rounded-full bg-surface px-3 py-1 text-xs font-medium text-foreground">
          {form.category}
        </span>
      ) : (
        <span className="rounded-full bg-surface px-3 py-1 text-xs font-medium text-foreground">
          All categories
        </span>
      )}
    </section>
  );
}

function ResultsFilters({
  form,
  onUpdateFilters,
}: {
  form: BeautyProfileForm;
  onUpdateFilters: (form: BeautyProfileForm) => void;
}) {
  return (
    <div className="space-y-4 border-t border-border pt-4">
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted">
          Category
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onUpdateFilters({ ...form, category: null })}
            className={`chip ${form.category === null ? "chip-selected" : "chip-default"}`}
          >
            All
          </button>
          {CATEGORY_OPTIONS.map((category) => (
            <button
              key={category}
              type="button"
              onClick={() => onUpdateFilters({ ...form, category })}
              className={`chip ${form.category === category ? "chip-selected" : "chip-default"}`}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted">
          Budget
        </p>
        <div className="flex flex-wrap gap-2">
          {BUDGET_PRESETS.map((preset) => (
            <button
              key={preset.value}
              type="button"
              onClick={() => onUpdateFilters({ ...form, budgetMaxUsd: preset.value })}
              className={`chip ${form.budgetMaxUsd === preset.value ? "chip-selected" : "chip-default"}`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">
            Exclusions
          </p>
          {form.exclusions.length > 0 ? (
            <button
              type="button"
              className="text-xs font-medium text-accent hover:text-accent-hover"
              onClick={() => onUpdateFilters({ ...form, exclusions: [] })}
            >
              Clear all
            </button>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {EXCLUSION_OPTIONS.map((option) => {
            const active = form.exclusions.includes(option.id);
            return (
              <button
                key={option.id}
                type="button"
                onClick={() => {
                  const exclusions = active
                    ? form.exclusions.filter((item) => item !== option.id)
                    : [...form.exclusions, option.id];
                  onUpdateFilters({ ...form, exclusions });
                }}
                className={`chip ${active ? "chip-selected" : "chip-default"}`}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
