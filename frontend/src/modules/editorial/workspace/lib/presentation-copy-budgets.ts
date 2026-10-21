/**
 * Copy budgets of the carousel presentation policies (mirrors the backend
 * contracts in ``backend/.../carousel-pipeline/contracts/*.yaml``).
 *
 * AE-0414: every ``hero_lower_third_v1..v4`` contract carries the SAME copy
 * budgets, so the budgets apply to every hero version (they used to apply to v1
 * only, which hid the live counter and the over-budget warning on v4 decks).
 * ``pov_hook_v1`` has its own (tighter hook) budgets. An unknown policy has no
 * budget: the editor still shows a plain character count.
 */
import type { LocalizedSlideReview } from "@/modules/editorial/workspace/types-ai";

export interface PresentationFieldBudget {
  maxCharacters: number;
  maxLines?: number;
}

/** AE-0414: the measured use of one field against its (optional) budget. */
export interface BudgetUsage {
  characters: number;
  lines: number;
  budget: PresentationFieldBudget | null;
  exceeded: boolean;
}

type BudgetTable = Readonly<Record<string, PresentationFieldBudget>>;

const SHARED_ITEM_BUDGETS: BudgetTable = {
  summary_point_body: { maxCharacters: 90 },
  feature_title: { maxCharacters: 32 },
  feature_body: { maxCharacters: 100 },
  closing_action_title: { maxCharacters: 30 },
  closing_action_body: { maxCharacters: 90 },
  cta_creator_name: { maxCharacters: 60 },
  cta_handle: { maxCharacters: 80 },
  cta_website: { maxCharacters: 80 },
};

const HERO_LOWER_THIRD_BUDGETS: BudgetTable = {
  ...SHARED_ITEM_BUDGETS,
  intro_heading: { maxCharacters: 72, maxLines: 3 },
  intro_subtitle: { maxCharacters: 180, maxLines: 4 },
  summary_heading: { maxCharacters: 64, maxLines: 3 },
  summary_point_title: { maxCharacters: 36 },
  content_heading: { maxCharacters: 64, maxLines: 3 },
  content_body: { maxCharacters: 220, maxLines: 6 },
};

const POV_HOOK_BUDGETS: BudgetTable = {
  ...SHARED_ITEM_BUDGETS,
  intro_heading: { maxCharacters: 60, maxLines: 3 },
  intro_subtitle: { maxCharacters: 40, maxLines: 1 },
  summary_heading: { maxCharacters: 64, maxLines: 3 },
  summary_point_title: { maxCharacters: 60 },
  content_heading: { maxCharacters: 64, maxLines: 3 },
  content_body: { maxCharacters: 200, maxLines: 6 },
};

const POLICY_BUDGETS: Readonly<Record<string, BudgetTable>> = {
  hero_lower_third_v1: HERO_LOWER_THIRD_BUDGETS,
  hero_lower_third_v2: HERO_LOWER_THIRD_BUDGETS,
  hero_lower_third_v3: HERO_LOWER_THIRD_BUDGETS,
  hero_lower_third_v4: HERO_LOWER_THIRD_BUDGETS,
  pov_hook_v1: POV_HOOK_BUDGETS,
};

/** The backend default policy (``DEFAULT_PRESENTATION_POLICY_VERSION``). */
const DEFAULT_POLICY_VERSION = "hero_lower_third_v1";

const SLIDE_TYPE_HEADING_BUDGET_KEY: Readonly<Record<string, string>> = {
  intro: "intro_heading",
  summary: "summary_heading",
  content: "content_heading",
  // Backend applies content_heading to closing/cta visible headings.
  closing: "content_heading",
  cta: "content_heading",
};

const SLIDE_TYPE_BODY_BUDGET_KEY: Readonly<Record<string, string>> = {
  intro: "intro_subtitle",
  content: "content_body",
};

/** Structured list key -> its budget key prefix (``{prefix}_{title|body}``). */
const ITEM_LIST_BUDGET_PREFIX: Readonly<Record<string, string>> = {
  summary_points: "summary_point",
  features: "feature",
  actions: "closing_action",
};

/** CTA string extras -> their budget key. */
const EXTRA_BUDGET_KEY: Readonly<Record<string, string>> = {
  creator_name: "cta_creator_name",
  creator_handle: "cta_handle",
  creator_website: "cta_website",
};

function budgetTable(policyVersion?: string | null): BudgetTable | null {
  if (!policyVersion) {
    return POLICY_BUDGETS[DEFAULT_POLICY_VERSION] ?? null;
  }
  return POLICY_BUDGETS[policyVersion] ?? null;
}

function lookupBudget(
  policyVersion: string | null | undefined,
  budgetKey: string | undefined,
): PresentationFieldBudget | null {
  if (!budgetKey) {
    return null;
  }
  return budgetTable(policyVersion)?.[budgetKey] ?? null;
}

export function resolveHeadingBudget(
  slideType: string,
  policyVersion?: string | null,
): PresentationFieldBudget | null {
  return lookupBudget(policyVersion, SLIDE_TYPE_HEADING_BUDGET_KEY[slideType]);
}

export function resolveBodyBudget(
  slideType: string,
  policyVersion?: string | null,
): PresentationFieldBudget | null {
  return lookupBudget(policyVersion, SLIDE_TYPE_BODY_BUDGET_KEY[slideType]);
}

/** AE-0414: budget of one structured item field (``features[0].title``). */
export function resolveItemBudget(
  listKey: string,
  field: string,
  policyVersion?: string | null,
): PresentationFieldBudget | null {
  const prefix = ITEM_LIST_BUDGET_PREFIX[listKey];
  return lookupBudget(policyVersion, prefix ? `${prefix}_${field}` : undefined);
}

/** AE-0414: budget of a CTA string extra (``creator_name``…). */
export function resolveExtraBudget(
  extraKey: string,
  policyVersion?: string | null,
): PresentationFieldBudget | null {
  return lookupBudget(policyVersion, EXTRA_BUDGET_KEY[extraKey]);
}

function countLines(value: string): number {
  return value.trim() ? value.split(/\r?\n/).length : 0;
}

export function isBudgetExceeded(
  value: string,
  budget: PresentationFieldBudget | null,
): boolean {
  if (!budget) {
    return false;
  }
  if (value.length > budget.maxCharacters) {
    return true;
  }
  return budget.maxLines !== undefined && countLines(value) > budget.maxLines;
}

/** AE-0414: live counter data for a field (always measured, budget optional). */
export function measureBudgetUsage(
  value: string,
  budget: PresentationFieldBudget | null,
): BudgetUsage {
  return {
    characters: value.length,
    lines: countLines(value),
    budget,
    exceeded: isBudgetExceeded(value, budget),
  };
}

export function formatBudgetUsage(
  value: string,
  budget: PresentationFieldBudget | null,
): string | null {
  if (!budget) {
    return null;
  }
  const lineSuffix =
    budget.maxLines !== undefined
      ? ` · ${countLines(value)}/${budget.maxLines} lines`
      : "";
  return `${value.length}/${budget.maxCharacters} chars${lineSuffix}`;
}

function textOf(presentation: Record<string, unknown>, key: string): string {
  const value = presentation[key];
  return typeof value === "string" ? value : "";
}

export function localizedSlidesHaveBudgetViolations(
  slides: LocalizedSlideReview[],
  policyVersion?: string | null,
): boolean {
  return slides.some((slide) => {
    const headingBudget = resolveHeadingBudget(slide.slide_type, policyVersion);
    const bodyBudget = resolveBodyBudget(slide.slide_type, policyVersion);
    return [slide.presentation_pt, slide.presentation_en].some(
      (presentation) =>
        isBudgetExceeded(textOf(presentation, "heading"), headingBudget) ||
        isBudgetExceeded(textOf(presentation, "body"), bodyBudget),
    );
  });
}
