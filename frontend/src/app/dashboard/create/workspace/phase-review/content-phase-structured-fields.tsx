"use client";

import { useTranslations } from "next-intl";
import {
  fieldDomId,
  fieldErrorKey,
  INSIGHT_QUOTE_EXTRA_KEY,
  parsePresentationInsightQuote,
  PresentationIconPreview,
  resolveExtraBudget,
  resolveItemBudget,
  structuredItemFieldPath,
  type PresentationLocaleKey,
  type SlideExtraEdit,
  type SlideFieldErrors,
  type SlideStructuredItemEdit,
} from "@/modules/editorial";
import type { LocalizedSlideReview } from "@/modules/publishing";
import { ContentCopyField } from "./content-phase-copy-field";
import { useStructuredExtraLabel } from "./content-phase-readonly-extras";

/** AE-0403: content-review DOM ids (``slide-{n}-{locale}-{field}``). */
export const CONTENT_REVIEW_ID_PREFIX = "slide";

/** Item fields the reviewer edits (``icon_name`` stays as generated). */
const ITEM_TEXT_FIELDS = ["title", "body"] as const;

/** Structured lists with a translated item label. */
const LABELLED_LISTS: ReadonlySet<string> = new Set([
  "summary_points",
  "features",
  "actions",
]);

/** Text fields of an object extra (``insight``) the reviewer can edit. */
const EXTRA_TEXT_FIELDS = ["title", "body", "quote", "attribution"] as const;

export interface StructuredEditContext {
  slide: LocalizedSlideReview;
  localeKey: PresentationLocaleKey;
  policyVersion?: string | null;
  fieldErrors: SlideFieldErrors;
  onItemChange: (edit: SlideStructuredItemEdit) => void;
  onExtraChange: (edit: SlideExtraEdit) => void;
}

/**
 * AE-0414: an extra the reviewer can edit — a string, or an object with at
 * least one text field. A ``pov_news`` quote card is a verified verbatim quote
 * (AE-0406/0407) and stays read-only.
 */
export function isEditableExtra(extraKey: string, value: unknown): boolean {
  if (typeof value === "string") {
    return true;
  }
  if (
    !value ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    (extraKey === INSIGHT_QUOTE_EXTRA_KEY &&
      parsePresentationInsightQuote(value) !== null)
  ) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return EXTRA_TEXT_FIELDS.some((field) => typeof record[field] === "string");
}

function asText(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function fieldProps(
  context: StructuredEditContext,
  fieldPath: string,
): { id: string; violations: ReturnType<SlideFieldErrors["get"]> } {
  const key = fieldErrorKey(
    context.slide.slide_index,
    context.localeKey,
    fieldPath,
  );
  return {
    id: fieldDomId(CONTENT_REVIEW_ID_PREFIX, key),
    violations: context.fieldErrors.get(key),
  };
}

/**
 * AE-0414 (B11): every item of a structured list (summary points, features,
 * closing actions) with an editable title and body, addressed by the same
 * ``list[i].field`` path the validator flags.
 */
export function EditableStructuredItems({
  context,
  listKey,
  items,
}: {
  context: StructuredEditContext;
  listKey: string;
  items: Record<string, unknown>[];
}): React.ReactElement {
  const tCopy = useTranslations("editorialWorkflow.review.copyField");
  return (
    <ul className="space-y-2 pt-1">
      {items.map((item, itemIndex) => (
        <li
          key={`${listKey}-${itemIndex}`}
          className="space-y-1 rounded-md border border-[var(--color-border)] p-2"
        >
          <p className="flex items-center gap-2 font-medium text-[var(--color-text-muted)] text-xs">
            {typeof item.icon_name === "string" && item.icon_name.trim() ? (
              <PresentationIconPreview
                iconName={item.icon_name.trim()}
                className="h-3.5 w-3.5 text-[var(--color-text)]"
              />
            ) : null}
            {tCopy("itemHeading", {
              list: LABELLED_LISTS.has(listKey)
                ? tCopy(`itemLists.${listKey}`)
                : listKey,
              index: itemIndex + 1,
            })}
          </p>
          {ITEM_TEXT_FIELDS.map((field) => (
            <ContentCopyField
              key={field}
              {...fieldProps(
                context,
                structuredItemFieldPath(listKey, itemIndex, field),
              )}
              label={tCopy(field === "title" ? "itemTitle" : "itemBody")}
              value={asText(item[field])}
              rows={field === "title" ? 1 : 2}
              localeKey={context.localeKey}
              budget={resolveItemBudget(listKey, field, context.policyVersion)}
              onChange={(value) =>
                context.onItemChange({
                  slideIndex: context.slide.slide_index,
                  locale: context.localeKey,
                  listKey,
                  itemIndex,
                  field,
                  value,
                })
              }
            />
          ))}
        </li>
      ))}
    </ul>
  );
}

/**
 * AE-0414 (B11): a free-text extra — a string (``tldr_strip``, the CTA
 * ``creator_*`` fields) or the text fields of an object (``insight``).
 * Returns null for any other shape (it stays read-only).
 */
export function EditableStructuredExtra({
  context,
  extraKey,
  value,
}: {
  context: StructuredEditContext;
  extraKey: string;
  value: unknown;
}): React.ReactElement | null {
  const tCopy = useTranslations("editorialWorkflow.review.copyField");
  const extraLabel = useStructuredExtraLabel();
  const edit = (field: string | undefined, next: string): void =>
    context.onExtraChange({
      slideIndex: context.slide.slide_index,
      locale: context.localeKey,
      extraKey,
      field,
      value: next,
    });
  if (typeof value === "string") {
    return (
      <ContentCopyField
        {...fieldProps(context, extraKey)}
        label={extraLabel(extraKey)}
        value={value}
        rows={1}
        localeKey={context.localeKey}
        budget={resolveExtraBudget(extraKey, context.policyVersion)}
        onChange={(next) => edit(undefined, next)}
      />
    );
  }
  const record =
    value && typeof value === "object" && !Array.isArray(value)
      ? (value as Record<string, unknown>)
      : {};
  const fields = EXTRA_TEXT_FIELDS.filter(
    (field) => typeof record[field] === "string",
  );
  if (fields.length === 0) {
    return null;
  }
  return (
    <div className="space-y-1">
      {fields.map((field) => (
        <ContentCopyField
          key={field}
          {...fieldProps(context, `${extraKey}.${field}`)}
          label={tCopy("extraPart", {
            field: extraLabel(extraKey),
            part: tCopy(`extraParts.${field}`),
          })}
          value={asText(record[field])}
          rows={2}
          localeKey={context.localeKey}
          budget={null}
          onChange={(next) => edit(field, next)}
        />
      ))}
    </div>
  );
}
