"use client";

import { useTranslations } from "next-intl";

import {
  CHECKLIST_BODY_FIELD,
  CHECKLIST_ITEM_FIELD,
  checklistItemEdit,
  checklistItemText,
  DISPLAYED_ITEM_FIELDS,
  fieldDomId,
  fieldErrorKey,
  resolveItemBudget,
  structuredItemFieldPath,
  type SlideFieldErrors,
} from "@/modules/editorial";

import { ContentCopyField } from "./content-phase-copy-field";
import type {
  ItemTextFieldsProps,
  StructuredEditContext,
} from "./content-phase-item-buttons";

/** Content-review DOM ids (``slide-{n}-{locale}-{field}``). */
export const CONTENT_REVIEW_ID_PREFIX = "slide";

export function asText(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function fieldProps(
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
 * The text fields of one item, as the slide shows them: the single line of a
 * checklist slide (title, else body) plus the body it does not draw, else the
 * title and the body. ``icon_name`` stays as generated.
 */
export function ItemTextFields({
  context,
  listKey,
  itemIndex,
  item,
}: Readonly<ItemTextFieldsProps>): React.ReactElement {
  const tCopy = useTranslations("editorialWorkflow.review.copyField");
  const base = {
    slideIndex: context.slide.slide_index,
    locale: context.localeKey,
    listKey,
    itemIndex,
  };
  const budgetOf = (field: string) =>
    resolveItemBudget(listKey, field, context.policyVersion);
  if (context.slide.checklist) {
    return (
      <>
        <ContentCopyField
          {...fieldProps(
            context,
            structuredItemFieldPath(listKey, itemIndex, CHECKLIST_ITEM_FIELD),
          )}
          label={tCopy("checklistLine")}
          value={checklistItemText(item)}
          rows={2}
          localeKey={context.localeKey}
          budget={budgetOf(CHECKLIST_ITEM_FIELD)}
          onChange={(value) =>
            context.onItemChange(checklistItemEdit({ ...base, value }))
          }
        />
        <ContentCopyField
          {...fieldProps(
            context,
            structuredItemFieldPath(listKey, itemIndex, CHECKLIST_BODY_FIELD),
          )}
          label={tCopy("checklistLineBody")}
          value={asText(item[CHECKLIST_BODY_FIELD])}
          rows={2}
          localeKey={context.localeKey}
          budget={budgetOf(CHECKLIST_BODY_FIELD)}
          onChange={(value) =>
            context.onItemChange({
              ...base,
              field: CHECKLIST_BODY_FIELD,
              value,
            })
          }
        />
      </>
    );
  }
  return (
    <>
      {DISPLAYED_ITEM_FIELDS.map((field) => (
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
          budget={budgetOf(field)}
          onChange={(value) => context.onItemChange({ ...base, field, value })}
        />
      ))}
    </>
  );
}
