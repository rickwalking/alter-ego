import {
  SLIDE_TYPE_ITEM_LIST_KEY,
  STRUCTURED_ITEM_DEFAULT_ICONS,
  STRUCTURED_LIST_MAX_ITEMS,
} from "@/constants/editorial-workflow";
import type { LocalizedSlideReview } from "@/modules/editorial/workspace/types-ai";
import {
  mirrorLocaleStructure,
  otherLocaleKey,
  type PresentationLocaleKey,
} from "./presentation-locale-mirror";
import {
  isPresentationStructuredItemList,
  PRESENTATION_STRUCTURED_ITEM_LIST_KEYS,
} from "./presentation-review-utils";

/**
 * AE-0437: add and remove structured list items in the content review.
 *
 * Prod carousel 7acaf967: the closing slide had ``actions: []`` and the editor
 * showed "Campo estruturado: actions []" with no way to add an item, so the
 * owner was stuck until a revision happened to produce them. Each slide type
 * now edits its own list key (a closing slide edits ``actions``, never a
 * stray ``features``), an empty list is offered with an "add item" slot, and
 * items can be removed. PT and EN keep the same shape (the gate blocks a
 * ``translation_shape_mismatch``), so adding or removing a slot changes both
 * locales at the same position; new slots start empty in both.
 */

export type StructuredListOperation = "add" | "remove";

export interface SlideStructuredListEdit {
  slideIndex: number;
  listKey: string;
  operation: StructuredListOperation;
  /** The item to remove (ignored for ``add``). */
  itemIndex?: number;
}

/** The list key a slide edits: its own type's list, else an existing one. */
export function editableStructuredListKey(
  presentation: Record<string, unknown>,
  slideType: string,
): string | null {
  const expected = SLIDE_TYPE_ITEM_LIST_KEY[slideType];
  if (expected && isPresentationStructuredItemList(presentation[expected])) {
    return expected;
  }
  const existing = PRESENTATION_STRUCTURED_ITEM_LIST_KEYS.find((key) =>
    isPresentationStructuredItemList(presentation[key]),
  );
  return existing ?? expected ?? null;
}

/** True when another item still fits the list. */
export function canAddStructuredItem(items: readonly unknown[]): boolean {
  return items.length < STRUCTURED_LIST_MAX_ITEMS;
}

function listOf(presentation: Record<string, unknown>, key: string): unknown[] {
  const value = presentation[key];
  return Array.isArray(value) ? value : [];
}

function newItem(position: number): Record<string, unknown> {
  const icons = STRUCTURED_ITEM_DEFAULT_ICONS;
  return { icon_name: icons[position % icons.length], title: "", body: "" };
}

function nextItems(items: unknown[], edit: SlideStructuredListEdit): unknown[] {
  if (edit.operation === "add") {
    return canAddStructuredItem(items)
      ? [...items, newItem(items.length)]
      : items;
  }
  return items.filter((_, index) => index !== edit.itemIndex);
}

function editedLocale(
  slide: LocalizedSlideReview,
  locale: PresentationLocaleKey,
  edit: SlideStructuredListEdit,
): Record<string, unknown> {
  // AE-0430: start from what the column shows (its own + mirrored structure).
  const presentation = mirrorLocaleStructure(
    slide[locale],
    slide[otherLocaleKey(locale)],
  );
  const items = listOf(presentation, edit.listKey);
  return { ...presentation, [edit.listKey]: nextItems(items, edit) };
}

/** Add or remove one slot of a structured list, in PT and EN together. */
export function applySlideStructuredListEdit(
  slides: LocalizedSlideReview[],
  edit: SlideStructuredListEdit,
): LocalizedSlideReview[] {
  return slides.map((slide) => {
    if (slide.slide_index !== edit.slideIndex) {
      return slide;
    }
    return {
      ...slide,
      presentation_pt: editedLocale(slide, "presentation_pt", edit),
      presentation_en: editedLocale(slide, "presentation_en", edit),
    };
  });
}
