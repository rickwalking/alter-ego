"use client";

import { useTranslations } from "next-intl";

import {
  INSIGHT_QUOTE_EXTRA_KEY,
  parsePresentationInsightQuote,
  PresentationIconPreview,
  resolveExtraBudget,
} from "@/modules/editorial";

import { ContentCopyField } from "./content-phase-copy-field";
import { useStructuredExtraLabel } from "./content-phase-readonly-extras";
import {
  listLabel,
  RemoveItemButton,
  AddItemButton,
} from "./content-phase-item-buttons";
import type { StructuredEditContext } from "./content-phase-item-buttons";
import {
  asText,
  fieldProps,
  ItemTextFields,
} from "./content-phase-item-text-fields";

export { CONTENT_REVIEW_ID_PREFIX } from "./content-phase-item-text-fields";

/** Text fields of an object extra (``insight``) the reviewer can edit. */
const EXTRA_TEXT_FIELDS = ["title", "body", "quote", "attribution"] as const;

/**
 * An extra the reviewer can edit — a string, or an object with at
 * least one text field. A ``pov_news`` quote card is a verified verbatim quote
 * and stays read-only.
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

/**
 * Every item of a structured list (summary points, features,
 * closing actions) with its displayed text editable, addressed by the same
 * ``list[i].field`` path the validator flags. Items can be added
 * (also to an empty list) and removed.
 */
export function EditableStructuredItems({
  context,
  listKey,
  items,
}: Readonly<{
  context: StructuredEditContext;
  listKey: string;
  items: Record<string, unknown>[];
}>): React.ReactElement {
  const tCopy = useTranslations("editorialWorkflow.review.copyField");
  return (
    <div className="space-y-2 pt-1">
      <ul className="space-y-2">
        {items.map((item, itemIndex) => (
          <li
            key={`${listKey}-${itemIndex}`}
            className="space-y-1 rounded-md border border-[var(--color-border)] p-2"
          >
            <div className="flex items-center gap-2 font-medium text-[var(--color-text-muted)] text-xs">
              {typeof item.icon_name === "string" && item.icon_name.trim() ? (
                <PresentationIconPreview
                  iconName={item.icon_name.trim()}
                  className="h-3.5 w-3.5 text-[var(--color-text)]"
                />
              ) : null}
              <span>
                {tCopy("itemHeading", {
                  list: listLabel(tCopy, listKey),
                  index: itemIndex + 1,
                })}
              </span>
              <RemoveItemButton
                context={context}
                listKey={listKey}
                itemIndex={itemIndex}
              />
            </div>
            <ItemTextFields
              context={context}
              listKey={listKey}
              itemIndex={itemIndex}
              item={item}
            />
          </li>
        ))}
      </ul>
      <AddItemButton context={context} listKey={listKey} items={items} />
    </div>
  );
}

/**
 * A free-text extra — a string (``tldr_strip``, the CTA
 * ``creator_*`` fields) or the text fields of an object (``insight``).
 * Returns null for any other shape (it stays read-only).
 */
export function EditableStructuredExtra({
  context,
  extraKey,
  value,
}: Readonly<{
  context: StructuredEditContext;
  extraKey: string;
  value: unknown;
}>): React.ReactElement | null {
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
export type { StructuredEditContext } from "./content-phase-item-buttons";
