import type { Concern, Exclusion, SkinType } from "@/lib/types";

export const SKIN_TYPE_OPTIONS: {
  id: SkinType;
  label: string;
  hint: string;
}[] = [
  { id: "dry", label: "Dry", hint: "Seeks moisture and barrier comfort" },
  { id: "oily", label: "Oily", hint: "Shine control and pore care" },
  { id: "combination", label: "Combination", hint: "Mixed zones, balanced care" },
  { id: "normal", label: "Normal", hint: "Maintenance and targeted goals" },
];

export const CONCERN_OPTIONS: { id: Concern; label: string }[] = [
  { id: "hydration", label: "Hydration" },
  { id: "acne_oil_control", label: "Acne & oil control" },
  { id: "brightening", label: "Brightening" },
  { id: "barrier_support", label: "Barrier support" },
  { id: "anti_aging", label: "Anti-aging" },
];

export const EXCLUSION_OPTIONS: { id: Exclusion; label: string }[] = [
  { id: "fragrance", label: "Fragrance-free" },
  { id: "drying_alcohol", label: "No drying alcohol" },
  { id: "paraben", label: "Paraben-free" },
  { id: "sulfate", label: "Sulfate-free" },
];

export const BUDGET_PRESETS = [
  { value: 30, label: "$30" },
  { value: 50, label: "$50" },
  { value: 75, label: "$75" },
  { value: 100, label: "$100" },
  { value: 150, label: "$150" },
  { value: 9999, label: "No limit" },
] as const;

export const CATEGORY_OPTIONS = [
  "Moisturizers",
  "Face Serums",
  "Cleansers",
  "Toners",
  "Sunscreen",
  "Eye Creams & Treatments",
  "Face Masks",
  "Face Oils",
  "Treatments",
] as const;

export const ONBOARDING_STEPS = [
  "Skin type",
  "Concerns",
  "Exclusions",
  "Budget & category",
  "Review",
] as const;

export function concernLabel(id: string): string {
  return CONCERN_OPTIONS.find((item) => item.id === id)?.label ?? id.replaceAll("_", " ");
}

export function skinTypeLabel(id: string): string {
  return SKIN_TYPE_OPTIONS.find((item) => item.id === id)?.label ?? id;
}

export function exclusionLabel(id: string): string {
  return EXCLUSION_OPTIONS.find((item) => item.id === id)?.label ?? id.replaceAll("_", " ");
}

export function formatPrice(value: number): string {
  if (value >= 9999) return "Any budget";
  return `$${value.toFixed(value % 1 === 0 ? 0 : 2)}`;
}

export function formatScore(value: number): string {
  return `${Math.round(value * 100)}% match`;
}
