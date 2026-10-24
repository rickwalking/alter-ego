"use client";

import { useTranslations } from "next-intl";

import {
  CHECKLIST_ITEM_FIELD,
  checklistItemEdit,
  checklistItemText,
  DISPLAYED_ITEM_FIELDS,
  fieldDomId,
  fieldErrorKey,
  resolveItemBudget,
  structuredItemFieldPath,
  type SlideFieldErrors,
  type SlideValidationViolation,
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

function checklistViolations(
  context: StructuredEditContext,
  listKey: string,
  itemIndex: number,
): SlideValidationViolation[] | undefined {
  const found = DISPLAYED_ITEM_FIELDS.flatMap(
    (field) =>
      fieldProps(context, structuredItemFieldPath(listKey, itemIndex, field))
        .violations ?? [],
  );
  return found.length > 0 ? found : undefined;
}

/**
 * The text fields of one item, as the slide shows them: the single line of a
 * checklist slide (title, else body; editing it clears the hidden body), else
 * the title and the body. ``icon_name`` stays as generated.
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
      <ContentCopyField
        id={
          fieldProps(
            context,
            structuredItemFieldPath(listKey, itemIndex, CHECKLIST_ITEM_FIELD),
          ).id
        }
        violations={checklistViolations(context, listKey, itemIndex)}
        label={tCopy("checklistLine")}
        value={checklistItemText(item)}
        rows={2}
        localeKey={context.localeKey}
        budget={budgetOf(CHECKLIST_ITEM_FIELD)}
        onChange={(value) =>
          context.onItemChange(checklistItemEdit({ ...base, value }))
        }
      />
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
