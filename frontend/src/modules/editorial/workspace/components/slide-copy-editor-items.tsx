"use client";

import { useTranslations } from "next-intl";
import { PRESENTATION_STRUCTURED_ITEM_LIST_KEYS } from "@/modules/editorial/workspace/lib/presentation-review-utils";
import {
  formatBudgetUsage,
  isBudgetExceeded,
  resolveBodyBudget,
} from "@/modules/editorial/workspace/lib/presentation-copy-budgets";
import {
  CHECKLIST_ITEM_FIELD,
  checklistItemEdit,
  checklistItemText,
  checklistLines,
  DISPLAYED_ITEM_FIELDS,
} from "@/modules/editorial/workspace/lib/checklist-items";
import type {
  PresentationLocaleKey,
  SlideStructuredItemEdit,
  StructuredItemField,
} from "@/modules/editorial/workspace/lib/presentation-slide-resolution";
import {
  fieldDomId,
  fieldErrorKey,
  structuredItemFieldPath,
} from "@/modules/editorial/workspace/lib/slide-field-errors";
import type {
  LocalizedSlideReview,
  SlideValidationViolation,
} from "@/modules/editorial/workspace/types-ai";
import { FlaggableTextarea, ListErrors } from "./slide-field-errors";
import type {
  ShownItems,
  SlideCopyEditorProps,
  StructuredItemFieldsProps,
  StructuredList,
} from "./types";

const ITEM_FIELD_LABEL_KEYS: Record<StructuredItemField, string> = {
  title: "structuredItemTitleLabel",
  body: "structuredItemLabel",
};

export function resolveStructuredList(
  presentation: Record<string, unknown>,
): StructuredList | null {
  for (const listKey of PRESENTATION_STRUCTURED_ITEM_LIST_KEYS) {
    const value = presentation[listKey];
    if (Array.isArray(value) && value.length > 0) {
      return { listKey, items: value as Record<string, unknown>[] };
    }
  }
  return null;
}

export function BudgetHint({
  value,
  slideType,
  policyVersion,
}: Readonly<{
  value: string;
  slideType: string;
  policyVersion?: string | null;
}>): React.ReactElement | null {
  const budget = resolveBodyBudget(slideType, policyVersion);
  const usage = formatBudgetUsage(value, budget);
  if (!usage) {
    return null;
  }
  const exceeded = isBudgetExceeded(value, budget);
  return (
    <p
      className={
        exceeded
          ? "text-destructive text-xs"
          : "text-[var(--color-text-muted)] text-xs"
      }
      role={exceeded ? "alert" : undefined}
    >
      {usage}
    </p>
  );
}

function itemViolations(
  props: SlideCopyEditorProps,
  keys: readonly string[],
): SlideValidationViolation[] | undefined {
  const found = keys.flatMap((key) => props.fieldErrors?.get(key) ?? []);
  return found.length > 0 ? found : undefined;
}

function StructuredItemFields({
  slide,
  locale,
  list,
  itemIndex,
  position,
  onChange,
  props,
}: Readonly<StructuredItemFieldsProps>): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const item = list.items[itemIndex] ?? {};
  const keyOf = (field: StructuredItemField): string =>
    fieldErrorKey(
      slide.slide_index,
      locale,
      structuredItemFieldPath(list.listKey, itemIndex, field),
    );
  const base = {
    slideIndex: slide.slide_index,
    locale,
    listKey: list.listKey,
    itemIndex,
  };
  const index = position + 1;
  if (slide.checklist) {
    const key = keyOf(CHECKLIST_ITEM_FIELD);
    return (
      <FlaggableTextarea
        id={fieldDomId(props.idPrefix, key)}
        violations={itemViolations(props, DISPLAYED_ITEM_FIELDS.map(keyOf))}
        aria-label={t("checklistItemLabel", { index })}
        value={checklistItemText(item)}
        rows={2}
        onChange={(event) =>
          onChange(checklistItemEdit({ ...base, value: event.target.value }))
        }
      />
    );
  }
  return (
    <>
      {DISPLAYED_ITEM_FIELDS.map((field) => (
        <FlaggableTextarea
          key={field}
          id={fieldDomId(props.idPrefix, keyOf(field))}
          violations={props.fieldErrors?.get(keyOf(field))}
          aria-label={t(ITEM_FIELD_LABEL_KEYS[field], { index })}
          value={typeof item[field] === "string" ? item[field] : ""}
          rows={field === CHECKLIST_ITEM_FIELD ? 1 : 2}
          onChange={(event) =>
            onChange({ ...base, field, value: event.target.value })
          }
        />
      ))}
    </>
  );
}

/**
 * The list a slide shows and the items of it the editor offers: on a
 * checklist slide only the lines the template draws (blank items dropped, at
 * most five), else every item.
 */
function shownItems(
  slide: LocalizedSlideReview,
  locale: PresentationLocaleKey,
): ShownItems | null {
  const presentation = slide[locale];
  if (!slide.checklist) {
    const list = resolveStructuredList(presentation);
    return list && { list, itemIndexes: list.items.map((_item, i) => i) };
  }
  const shown = checklistLines(presentation);
  if (shown === null) {
    return null;
  }
  const items = presentation[shown.listKey] as Record<string, unknown>[];
  return {
    list: { listKey: shown.listKey, items },
    itemIndexes: shown.lines.map((line) => line.itemIndex),
  };
}

/**
 * The slide's structured items, editing exactly what the slide shows: one
 * line per drawn item on a checklist slide, else title and body; list errors on top.
 */
export function StructuredItemsEditor({
  slide,
  locale,
  onChange,
  props,
}: Readonly<{
  slide: LocalizedSlideReview;
  locale: PresentationLocaleKey;
  onChange: (edit: SlideStructuredItemEdit) => void;
  props: SlideCopyEditorProps;
}>): React.ReactElement | null {
  const t = useTranslations("editorialWorkflow.review");
  const shown = shownItems(slide, locale);
  const listErrors = <ListErrors slide={slide} locale={locale} props={props} />;
  if (shown === null) {
    return listErrors;
  }
  return (
    <div className="space-y-1">
      <p className="font-medium text-[var(--color-text-muted)] text-xs">
        {t("structuredItems")}
      </p>
      {listErrors}
      {shown.itemIndexes.map((itemIndex, position) => (
        <StructuredItemFields
          key={`${shown.list.listKey}-${itemIndex}`}
          slide={slide}
          locale={locale}
          list={shown.list}
          itemIndex={itemIndex}
          position={position}
          onChange={onChange}
          props={props}
        />
      ))}
    </div>
  );
}
