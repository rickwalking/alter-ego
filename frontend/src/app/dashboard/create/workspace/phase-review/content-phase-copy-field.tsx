"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import {
  EMPHASIS_EXAMPLE_BY_LOCALE,
  emphasisConventionMismatch,
  FlaggableTextarea,
  measureBudgetUsage,
  normalizeEmphasis,
  type PresentationFieldBudget,
  type PresentationLocaleKey,
  type SlideValidationViolation,
} from "@/modules/editorial";

export interface ContentCopyFieldProps {
  id: string;
  label: string;
  value: string;
  rows: number;
  localeKey: PresentationLocaleKey;
  budget: PresentationFieldBudget | null;
  violations: SlideValidationViolation[] | undefined;
  onChange: (value: string) => void;
}

/**
 * AE-0414 (B29): live length counter under a content field. Always shows the
 * character count; with a known budget it shows ``n/max`` (and lines) and turns
 * into an alert once the copy is over budget.
 */
export function CopyLengthCounter({
  value,
  budget,
}: Readonly<{
  value: string;
  budget: PresentationFieldBudget | null;
}>): React.ReactElement {
  const tCopy = useTranslations("editorialWorkflow.review.copyField");
  const usage = measureBudgetUsage(value, budget);
  const parts = [
    budget
      ? tCopy("charsOfMax", {
          count: usage.characters,
          max: budget.maxCharacters,
        })
      : tCopy("chars", { count: usage.characters }),
  ];
  if (budget?.maxLines !== undefined) {
    parts.push(
      tCopy("linesOfMax", { count: usage.lines, max: budget.maxLines }),
    );
  }
  if (usage.exceeded) {
    parts.push(tCopy("overBudget"));
  }
  return (
    <p
      className={
        usage.exceeded
          ? "text-destructive text-xs"
          : "text-[var(--color-text-muted)] text-xs"
      }
      role={usage.exceeded ? "alert" : undefined}
      data-testid="copy-length-counter"
    >
      {parts.join(" · ")}
    </p>
  );
}

/** AE-0414 (B29): copy written with the other locale's emphasis markup. */
function EmphasisMismatch({
  localeKey,
  value,
  onChange,
}: Readonly<{
  localeKey: PresentationLocaleKey;
  value: string;
  onChange: (value: string) => void;
}>): React.ReactElement | null {
  const tCopy = useTranslations("editorialWorkflow.review.copyField");
  if (!emphasisConventionMismatch(localeKey, value)) {
    return null;
  }
  return (
    <div className="flex flex-wrap items-center gap-2 text-[var(--color-warning,#b45309)] text-xs">
      <span>
        {tCopy("emphasisMismatch", {
          example: EMPHASIS_EXAMPLE_BY_LOCALE[localeKey],
        })}
      </span>
      <NeonButton
        size="sm"
        variant="outline"
        onClick={() => onChange(normalizeEmphasis(localeKey, value))}
      >
        {tCopy("emphasisConvert")}
      </NeonButton>
    </div>
  );
}

/** One editable content-review field: textarea + errors + counter + markup. */
export function ContentCopyField(
  props: Readonly<ContentCopyFieldProps>,
): React.ReactElement {
  return (
    <div className="space-y-1">
      <label
        className="font-medium text-[var(--color-text-muted)] text-xs"
        htmlFor={props.id}
      >
        {props.label}
      </label>
      <FlaggableTextarea
        id={props.id}
        violations={props.violations}
        value={props.value}
        rows={props.rows}
        onChange={(event) => props.onChange(event.target.value)}
      />
      <CopyLengthCounter value={props.value} budget={props.budget} />
      <EmphasisMismatch
        localeKey={props.localeKey}
        value={props.value}
        onChange={props.onChange}
      />
    </div>
  );
}

/** AE-0414 (B29): the locale's emphasis convention, shown once per column. */
export function EmphasisConventionHint({
  localeKey,
}: Readonly<{
  localeKey: PresentationLocaleKey;
}>): React.ReactElement {
  const tCopy = useTranslations("editorialWorkflow.review.copyField");
  return (
    <p className="text-[var(--color-text-muted)] text-xs">
      {tCopy("emphasisHint", {
        example: EMPHASIS_EXAMPLE_BY_LOCALE[localeKey],
      })}
    </p>
  );
}
