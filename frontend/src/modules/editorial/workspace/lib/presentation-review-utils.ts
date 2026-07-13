import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
  SlideValidationViolation,
  ViolationSeverity,
} from "@/modules/editorial/workspace/types-ai";

/** AE-0312: warning-tier casing violations render distinctly from blockers. */
export const VIOLATION_SEVERITY_WARNING: ViolationSeverity = "warning";
export const VIOLATION_SEVERITY_BLOCKER: ViolationSeverity = "blocker";

export function isWarningViolation(
  violation: SlideValidationViolation,
): boolean {
  return violation.severity === VIOLATION_SEVERITY_WARNING;
}

/**
 * AE-0312: non-blocking warnings get a muted/amber treatment; blockers keep the
 * destructive treatment. A violation with no severity defaults to blocker.
 */
export function violationToneClasses(
  violation: SlideValidationViolation,
): string {
  return isWarningViolation(violation)
    ? "text-[var(--color-warning,#b45309)]"
    : "text-destructive";
}

export const PRESENTATION_STRUCTURED_EXTRA_KEYS = [
  "features",
  "stats",
  "insight",
  "summary_points",
  "actions",
  "tldr_strip",
  "content_kind",
  "creator_name",
  "creator_handle",
  "creator_website",
] as const;

export const PRESENTATION_STRUCTURED_ITEM_LIST_KEYS = [
  "summary_points",
  "features",
  "actions",
] as const;

export interface PresentationStructuredItem {
  icon_name?: string;
  title?: string;
  body?: string;
}

export interface PresentationFieldBudget {
  maxCharacters: number;
  maxLines?: number;
}

const HERO_LOWER_THIRD_V1_BUDGETS: Record<string, PresentationFieldBudget> = {
  intro_heading: { maxCharacters: 72, maxLines: 3 },
  intro_subtitle: { maxCharacters: 180, maxLines: 4 },
  summary_heading: { maxCharacters: 64, maxLines: 3 },
  content_heading: { maxCharacters: 64, maxLines: 3 },
  content_body: { maxCharacters: 220, maxLines: 6 },
  closing_action_title: { maxCharacters: 30 },
  closing_action_body: { maxCharacters: 90 },
  cta_creator_name: { maxCharacters: 60 },
  cta_handle: { maxCharacters: 80 },
  cta_website: { maxCharacters: 80 },
};

const SLIDE_TYPE_HEADING_BUDGET_KEY: Record<string, string> = {
  intro: "intro_heading",
  summary: "summary_heading",
  content: "content_heading",
  // Backend applies content_heading to closing/cta visible headings.
  closing: "content_heading",
  cta: "content_heading",
};

const SLIDE_TYPE_BODY_BUDGET_KEY: Record<string, string> = {
  intro: "intro_subtitle",
  content: "content_body",
};

export function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : {};
}

export function presentationHeading(
  presentation: Record<string, unknown>,
  fallback: string,
): string {
  const heading = presentation.heading;
  return typeof heading === "string" && heading.trim() ? heading : fallback;
}

export function presentationBody(
  presentation: Record<string, unknown>,
): string {
  const body = presentation.body;
  return typeof body === "string" ? body : "";
}

export function resolveSlideDraftTitle(
  slide: Record<string, unknown>,
  fallback: string,
): string {
  const presentationPt = asRecord(slide.presentation_pt);
  const ptHeading = presentationHeading(presentationPt, "");
  if (ptHeading.trim()) {
    return ptHeading;
  }
  const title = slide.title;
  if (typeof title === "string" && title.trim()) {
    return title;
  }
  const heading = slide.heading;
  if (typeof heading === "string" && heading.trim()) {
    return heading;
  }
  return fallback;
}

export function resolveSlideDraftPreview(
  slide: Record<string, unknown>,
): string {
  const presentationPt = asRecord(slide.presentation_pt);
  const preview = resolvePresentationPreviewText(presentationPt);
  if (preview.trim()) {
    return preview;
  }
  const ptHeading = presentationHeading(presentationPt, "");
  if (ptHeading.trim()) {
    return ptHeading;
  }
  const draftText = slide.draft_text;
  if (
    typeof draftText === "string" &&
    draftText.trim() &&
    !draftText.trim().startsWith("{")
  ) {
    return draftText;
  }
  const body = slide.body;
  return typeof body === "string" ? body : "";
}

export function resolveHeadingBudget(
  slideType: string,
  policyVersion?: string | null,
): PresentationFieldBudget | null {
  if (policyVersion && policyVersion !== "hero_lower_third_v1") {
    return null;
  }
  const budgetKey = SLIDE_TYPE_HEADING_BUDGET_KEY[slideType];
  return budgetKey ? (HERO_LOWER_THIRD_V1_BUDGETS[budgetKey] ?? null) : null;
}

export function resolveBodyBudget(
  slideType: string,
  policyVersion?: string | null,
): PresentationFieldBudget | null {
  if (policyVersion && policyVersion !== "hero_lower_third_v1") {
    return null;
  }
  const budgetKey = SLIDE_TYPE_BODY_BUDGET_KEY[slideType];
  return budgetKey ? (HERO_LOWER_THIRD_V1_BUDGETS[budgetKey] ?? null) : null;
}

export function formatBudgetUsage(
  value: string,
  budget: PresentationFieldBudget | null,
): string | null {
  if (!budget) {
    return null;
  }
  const lineCount = value.trim() ? value.split(/\r?\n/).length : 0;
  const lineSuffix =
    budget.maxLines !== undefined
      ? ` · ${lineCount}/${budget.maxLines} lines`
      : "";
  return `${value.length}/${budget.maxCharacters} chars${lineSuffix}`;
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
  if (budget.maxLines !== undefined) {
    const lineCount = value.trim() ? value.split(/\r?\n/).length : 0;
    return lineCount > budget.maxLines;
  }
  return false;
}

export function localizedSlidesHaveBudgetViolations(
  slides: LocalizedSlideReview[],
  policyVersion?: string | null,
): boolean {
  return slides.some((slide) => {
    const headingBudget = resolveHeadingBudget(slide.slide_type, policyVersion);
    const bodyBudget = resolveBodyBudget(slide.slide_type, policyVersion);
    const ptHeading = presentationHeading(slide.presentation_pt, "");
    const ptBody = presentationBody(slide.presentation_pt);
    const enHeading = presentationHeading(slide.presentation_en, "");
    const enBody = presentationBody(slide.presentation_en);
    return (
      isBudgetExceeded(ptHeading, headingBudget) ||
      isBudgetExceeded(ptBody, bodyBudget) ||
      isBudgetExceeded(enHeading, headingBudget) ||
      isBudgetExceeded(enBody, bodyBudget)
    );
  });
}

export function isPresentationStructuredItem(
  value: unknown,
): value is PresentationStructuredItem {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

export function isPresentationStructuredItemList(
  value: unknown,
): value is PresentationStructuredItem[] {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every(isPresentationStructuredItem)
  );
}

export function listPresentationStructuredItems(
  presentation: Record<string, unknown>,
): PresentationStructuredItem[] {
  for (const key of PRESENTATION_STRUCTURED_ITEM_LIST_KEYS) {
    const value = presentation[key];
    if (isPresentationStructuredItemList(value)) {
      return value;
    }
  }
  return [];
}

function formatStructuredItem(item: PresentationStructuredItem): string | null {
  const title = typeof item.title === "string" ? item.title.trim() : "";
  const itemBody = typeof item.body === "string" ? item.body.trim() : "";
  if (title && itemBody) return `• ${title}: ${itemBody}`;
  if (title) return `• ${title}`;
  if (itemBody) return `• ${itemBody}`;
  return null;
}

export function resolvePresentationPreviewText(
  presentation: Record<string, unknown>,
): string {
  const parts: string[] = [];
  const body = presentationBody(presentation);
  if (body.trim() && !body.trim().startsWith("{")) {
    parts.push(body.trim());
  }
  for (const item of listPresentationStructuredItems(presentation)) {
    const formatted = formatStructuredItem(item);
    if (formatted) parts.push(formatted);
  }
  const tldr = presentation.tldr_strip;
  if (typeof tldr === "string" && tldr.trim()) {
    parts.push(tldr.trim());
  }
  return parts.join("\n");
}

export function listStructuredExtras(
  presentation: Record<string, unknown>,
): Array<{ key: string; value: unknown }> {
  return PRESENTATION_STRUCTURED_EXTRA_KEYS.flatMap((key) => {
    const value = presentation[key];
    if (value === undefined || value === null) {
      return [];
    }
    if (
      PRESENTATION_STRUCTURED_ITEM_LIST_KEYS.includes(
        key as (typeof PRESENTATION_STRUCTURED_ITEM_LIST_KEYS)[number],
      ) &&
      isPresentationStructuredItemList(value)
    ) {
      return [];
    }
    if (key === "content_kind") {
      return [];
    }
    return [{ key, value }];
  });
}

export function collectIconNames(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.flatMap((item) => collectIconNames(item));
  }
  if (!value || typeof value !== "object") {
    return [];
  }
  const record = value as Record<string, unknown>;
  const icons: string[] = [];
  const iconName = record.icon_name;
  if (typeof iconName === "string" && iconName.trim()) {
    icons.push(iconName.trim());
  }
  for (const nested of Object.values(record)) {
    icons.push(...collectIconNames(nested));
  }
  return icons;
}

export function listPresentationIconNames(
  presentation: Record<string, unknown>,
): string[] {
  return [...new Set(collectIconNames(presentation))];
}

export function hasBlockingPresentationViolations(
  state: EditorialWorkflowState | null | undefined,
): boolean {
  return state?.presentation_validation?.blocking === true;
}

export function listPresentationViolations(
  state: EditorialWorkflowState | null | undefined,
): SlideValidationViolation[] {
  return state?.presentation_validation?.violations ?? [];
}

/**
 * AE-0309: true when the content interrupt/gate payload carries a blocking
 * fail-closed report (validate -> repair -> retry all failed for a slide).
 */
export function hasBlockingContentGateValidation(
  state: EditorialWorkflowState | null | undefined,
): boolean {
  return state?.content_gate_validation?.blocking === true;
}

export function listContentGateViolations(
  state: EditorialWorkflowState | null | undefined,
): SlideValidationViolation[] {
  return state?.content_gate_validation?.violations ?? [];
}

function violationKey(violation: SlideValidationViolation): string {
  return [
    violation.code,
    violation.slide_index ?? "all",
    violation.locale ?? "locale",
    violation.field ?? "field",
  ].join("-");
}

/**
 * AE-0309: presentation violations merged with the ones arriving in the
 * content interrupt/gate payload, de-duplicated for a single review list.
 */
export function listContentReviewViolations(
  state: EditorialWorkflowState | null | undefined,
): SlideValidationViolation[] {
  const seen = new Set<string>();
  const merged: SlideValidationViolation[] = [];
  for (const violation of [
    ...listPresentationViolations(state),
    ...listContentGateViolations(state),
  ]) {
    const key = violationKey(violation);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    merged.push(violation);
  }
  return merged;
}
