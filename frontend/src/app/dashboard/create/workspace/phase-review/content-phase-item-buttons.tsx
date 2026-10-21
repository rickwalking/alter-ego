"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import {
  canAddStructuredItem,
  type PresentationLocaleKey,
  type SlideExtraEdit,
  type SlideFieldErrors,
  type SlideStructuredItemEdit,
  type SlideStructuredListEdit,
} from "@/modules/editorial";
import type { LocalizedSlideReview } from "@/modules/publishing";

/** Structured lists with a translated item label. */
export const LABELLED_LISTS: ReadonlySet<string> = new Set([
  "summary_points",
  "features",
  "actions",
]);

export interface StructuredEditContext {
  slide: LocalizedSlideReview;
  localeKey: PresentationLocaleKey;
  policyVersion?: string | null;
  fieldErrors: SlideFieldErrors;
  onItemChange: (edit: SlideStructuredItemEdit) => void;
  onExtraChange: (edit: SlideExtraEdit) => void;
  /** Add / remove item slots (PT and EN together). */
  onListChange?: (edit: SlideStructuredListEdit) => void;
}

export function listLabel(
  tCopy: ReturnType<typeof useTranslations>,
  listKey: string,
): string {
  return LABELLED_LISTS.has(listKey) ? tCopy(`itemLists.${listKey}`) : listKey;
}

/** The "remove this item" button (both locales, same position). */
export function RemoveItemButton({
  context,
  listKey,
  itemIndex,
}: Readonly<{
  context: StructuredEditContext;
  listKey: string;
  itemIndex: number;
}>): React.ReactElement | null {
  const tCopy = useTranslations("editorialWorkflow.review.copyField");
  const onListChange = context.onListChange;
  if (!onListChange) {
    return null;
  }
  return (
    <NeonButton
      type="button"
      size="sm"
      variant="ghost"
      className="ml-auto h-6 px-2"
      onClick={() =>
        onListChange({
          slideIndex: context.slide.slide_index,
          listKey,
          operation: "remove",
          itemIndex,
        })
      }
    >
      {tCopy("removeItem", {
        list: listLabel(tCopy, listKey),
        index: itemIndex + 1,
      })}
    </NeonButton>
  );
}

/** The "add an item" slot under the list (empty lists included). */
export function AddItemButton({
  context,
  listKey,
  items,
}: Readonly<{
  context: StructuredEditContext;
  listKey: string;
  items: Record<string, unknown>[];
}>): React.ReactElement | null {
  const tCopy = useTranslations("editorialWorkflow.review.copyField");
  const onListChange = context.onListChange;
  if (!onListChange || !canAddStructuredItem(items)) {
    return null;
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <NeonButton
        type="button"
        size="sm"
        variant="outline"
        onClick={() =>
          onListChange({
            slideIndex: context.slide.slide_index,
            listKey,
            operation: "add",
          })
        }
      >
        {tCopy("addItem", { list: listLabel(tCopy, listKey) })}
      </NeonButton>
      <span className="text-[var(--color-text-muted)] text-xs">
        {tCopy("itemSlotsHint")}
      </span>
    </div>
  );
}
