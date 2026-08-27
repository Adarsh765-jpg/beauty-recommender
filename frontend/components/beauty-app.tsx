"use client";

import type { ReactNode } from "react";
import { useMemo, useState } from "react";

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
import type {
  BeautyProfileForm,
  Concern,
  Exclusion,
  RecommendedProduct,
  RecommendResponse,
} from "@/lib/types";

type AppPhase = "landing" | "onboarding" | "loading" | "results";

const INITIAL_FORM: BeautyProfileForm = {
  skinType: null,
  concerns: [],
  exclusions: [],
  budgetMaxUsd: 75,
  category: null,
};

export function BeautyApp() {
  const [phase, setPhase] = useState<AppPhase>("landing");
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<BeautyProfileForm>(INITIAL_FORM);
  const [results, setResults] = useState<RecommendResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedProduct = useMemo(
    () => results?.items.find((item) => item.product_id === selectedId) ?? null,
    [results, selectedId],
  );

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

  async function submitProfile() {
    if (!form.skinType) return;

    setPhase("loading");
    setError(null);
    setResults(null);
    setSelectedId(null);

    try {
      const response = await fetchRecommendations({
        skin_type: form.skinType,
        concerns: form.concerns,
        exclusions: form.exclusions,
        budget_max_usd: form.budgetMaxUsd,
        category: form.category,
        top_k: 10,
      });
      setResults(response);
      if (response.items.length > 0) {
        setSelectedId(response.items[0].product_id);
      }
      setPhase("results");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Something went wrong.");
      setPhase("results");
    }
  }

  function restart() {
    setPhase("landing");
    setStep(0);
    setForm(INITIAL_FORM);
    setResults(null);
    setSelectedId(null);
    setError(null);
  }

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader showHome={phase !== "landing"} onHome={restart} />

      {phase === "landing" && (
        <main className="mx-auto max-w-4xl px-4 py-16 sm:px-6 sm:py-24">
          <h1 className="text-3xl font-bold leading-tight text-foreground sm:text-4xl">
            Skincare picks made for your skin
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-body">
            Answer a short quiz about your skin type, goals, and preferences. We&apos;ll recommend
            the best Sephora products for you — and explain every pick.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => {
                setPhase("onboarding");
                setStep(0);
              }}
              className="btn-primary"
            >
              Take the quiz
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
              Quick demo
            </button>
          </div>
        </main>
      )}

      {phase === "onboarding" && (
        <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
          <p className="mb-2 text-sm text-muted">
            Step {step + 1} of {ONBOARDING_STEPS.length}: {ONBOARDING_STEPS[step]}
          </p>
          <div className="mb-6 flex gap-1">
            {ONBOARDING_STEPS.map((label, index) => (
              <div
                key={label}
                className={`h-1 flex-1 ${index <= step ? "bg-accent" : "bg-border"}`}
              />
            ))}
          </div>

          <div className="rounded-sm border border-border bg-surface p-6 sm:p-8">
            {step === 0 && (
              <StepShell title="What's your skin type?" subtitle="We'll match products suited to your skin.">
                <div className="grid gap-3 sm:grid-cols-2">
                  {SKIN_TYPE_OPTIONS.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      onClick={() => setForm((current) => ({ ...current, skinType: option.id }))}
                      className={`rounded-sm border p-4 text-left transition ${
                        form.skinType === option.id
                          ? "border-accent bg-accent-soft"
                          : "border-border hover:border-accent/40"
                      }`}
                    >
                      <p className="font-semibold text-foreground">{option.label}</p>
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
                    <p className="mb-3 text-sm font-semibold text-foreground">Max budget</p>
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
                    <p className="mb-3 text-sm font-semibold text-foreground">Category</p>
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
                  onClick={submitProfile}
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
          <p className="mt-5 text-lg font-semibold text-foreground">Finding your best matches…</p>
        </main>
      )}

      {phase === "results" && (
        <ResultsView
          form={form}
          results={results}
          error={error}
          selectedProduct={selectedProduct}
          onSelect={(product) => setSelectedId(product.product_id)}
          onRestart={restart}
          onEditProfile={() => {
            setPhase("onboarding");
            setStep(4);
            setError(null);
          }}
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
      <h2 className="text-xl font-bold text-foreground">{title}</h2>
      <p className="mt-1 text-sm text-body">{subtitle}</p>
      <div className="mt-5">{children}</div>
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
  onSelect,
  onRestart,
  onEditProfile,
}: {
  form: BeautyProfileForm;
  results: RecommendResponse | null;
  error: string | null;
  selectedProduct: RecommendedProduct | null;
  onSelect: (product: RecommendedProduct) => void;
  onRestart: () => void;
  onEditProfile: () => void;
}) {
  if (error) {
    return (
      <main className="mx-auto max-w-lg px-4 py-16 text-center sm:px-6">
        <h2 className="text-xl font-bold text-foreground">Couldn&apos;t load recommendations</h2>
        <p className="mt-2 text-sm text-body">{error}</p>
        <div className="mt-6 flex justify-center gap-3">
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

  if (!results || results.status === "no_match" || results.items.length === 0) {
    return (
      <main className="mx-auto max-w-lg px-4 py-16 text-center sm:px-6">
        <h2 className="text-xl font-bold text-foreground">No products matched</h2>
        <p className="mt-2 text-sm text-body">Try relaxing your budget or filters.</p>
        {results?.relaxations.length ? (
          <ul className="mt-4 space-y-2 text-left text-sm text-body">
            {results.relaxations.map((item) => (
              <li key={item} className="rounded-sm border border-border bg-surface px-4 py-3">
                {item}
              </li>
            ))}
          </ul>
        ) : null}
        <div className="mt-6 flex justify-center gap-3">
          <button type="button" onClick={onEditProfile} className="btn-primary py-2.5">
            Adjust filters
          </button>
          <button type="button" onClick={onRestart} className="btn-secondary py-2.5">
            Start over
          </button>
        </div>
      </main>
    );
  }

  const filterChips: string[] = [];
  if (form.skinType) filterChips.push(skinTypeLabel(form.skinType));
  form.concerns.forEach((c) => filterChips.push(concernLabel(c)));
  filterChips.push(formatPrice(form.budgetMaxUsd));

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-foreground sm:text-2xl">
            {results.items.length} products for{" "}
            {form.skinType ? skinTypeLabel(form.skinType).toLowerCase() : "you"}
          </h2>
          <p className="mt-1 text-sm text-muted">
            From {results.candidate_count.toLocaleString()} products matching your filters
          </p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={onEditProfile} className="btn-secondary py-2 text-sm">
            Edit
          </button>
          <button type="button" onClick={onRestart} className="btn-secondary py-2 text-sm">
            Restart
          </button>
        </div>
      </div>

      <div className="mb-5 flex flex-wrap gap-2">
        {filterChips.map((chip) => (
          <span
            key={chip}
            className="rounded-sm border border-border bg-surface px-3 py-1 text-xs font-medium text-body"
          >
            {chip}
          </span>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-3">
          {results.items.map((product, index) => (
            <ProductCard
              key={product.product_id}
              product={product}
              rank={index + 1}
              selected={selectedProduct?.product_id === product.product_id}
              onSelect={() => onSelect(product)}
            />
          ))}
        </div>

        <WhyThisPanel product={selectedProduct} />
      </div>
    </main>
  );
}
