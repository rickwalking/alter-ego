"use client";

import { useTranslations } from "next-intl";
import { PRESENTATION_STRUCTURED_ITEM_LIST_KEYS } from "@/modules/editorial/workspace/lib/presentation-review-utils";
import {
  formatBudgetUsage,
  isBudgetExceeded,
  resolveBodyBudget,
} from "@/modules/editorial/workspace/lib/presentation-copy-budgets";
import type {
  PresentationLocaleKey,
  SlideStructuredItemEdit,
} from "@/modules/editorial/workspace/lib/presentation-slide-resolution";
import {
  fieldDomId,
  fieldErrorKey,
  structuredItemFieldPath,
} from "@/modules/editorial/workspace/lib/slide-field-errors";
import type { LocalizedSlideReview } from "@/modules/editorial/workspace/types-ai";
import { FlaggableTextarea } from "./slide-field-errors";
import type { SlideCopyEditorProps, StructuredList } from "./types";

export const ITEM_BODY_FIELD = "body";

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
}: {
  value: string;
  slideType: string;
  policyVersion?: string | null;
}): React.ReactElement | null {
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

export function StructuredItemsEditor({
  slide,
  locale,
  onChange,
  props,
}: {
  slide: LocalizedSlideReview;
  locale: PresentationLocaleKey;
  onChange: (edit: SlideStructuredItemEdit) => void;
  props: SlideCopyEditorProps;
}): React.ReactElement | null {
  const t = useTranslations("editorialWorkflow.review");
  const resolved = resolveStructuredList(slide[locale]);
  if (resolved === null) {
    return null;
  }
  return (
    <div className="space-y-1">
      <p className="font-medium text-[var(--color-text-muted)] text-xs">
        {t("structuredItems")}
      </p>
      {resolved.items.map((item, itemIndex) => {
        const key = fieldErrorKey(
          slide.slide_index,
          locale,
          structuredItemFieldPath(resolved.listKey, itemIndex, ITEM_BODY_FIELD),
        );
        return (
          <FlaggableTextarea
            key={key}
            id={fieldDomId(props.idPrefix, key)}
            violations={props.fieldErrors?.get(key)}
            aria-label={t("structuredItemLabel", { index: itemIndex + 1 })}
            value={typeof item.body === "string" ? item.body : ""}
            rows={2}
            onChange={(event) =>
              onChange({
                slideIndex: slide.slide_index,
                locale,
                listKey: resolved.listKey,
                itemIndex,
                field: ITEM_BODY_FIELD,
                value: event.target.value,
              })
            }
          />
        );
      })}
    </div>
  );
}
