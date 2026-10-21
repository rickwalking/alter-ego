import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
} from "@/modules/editorial/workspace/types-ai";
import {
  mirrorLocaleStructure,
  otherLocaleKey,
  type PresentationLocaleKey,
} from "./presentation-locale-mirror";
import {
  presentationBody,
  presentationHeading,
} from "./presentation-review-utils";

export type { PresentationLocaleKey } from "./presentation-locale-mirror";
export type EditableCopyField = "heading" | "body";

export interface SlideCopyEdit {
  slideIndex: number;
  locale: PresentationLocaleKey;
  field: EditableCopyField;
  value: string;
}

export function applySlideCopyEdit(
  slides: LocalizedSlideReview[],
  edit: SlideCopyEdit,
): LocalizedSlideReview[] {
  return slides.map((slide) => {
    if (slide.slide_index !== edit.slideIndex) {
      return slide;
    }
    return {
      ...slide,
      [edit.locale]: {
        ...slide[edit.locale],
        [edit.field]: edit.value,
      },
    };
  });
}

/**
 * AE-0314: structured-extras edit (summary points / closing features). Edits one
 * field (`title`/`body`) of one item in a locale's structured-item list, keeping
 * the rest of the item and the array immutable.
 */
export type StructuredItemField = "title" | "body";

export interface SlideStructuredItemEdit {
  slideIndex: number;
  locale: PresentationLocaleKey;
  listKey: string;
  itemIndex: number;
  field: StructuredItemField;
  value: string;
}

/** AE-0430: the locale payload plus the structure the other locale has. */
function editablePresentation(
  slide: LocalizedSlideReview,
  locale: PresentationLocaleKey,
): Record<string, unknown> {
  return mirrorLocaleStructure(slide[locale], slide[otherLocaleKey(locale)]);
}

export function applySlideStructuredItemEdit(
  slides: LocalizedSlideReview[],
  edit: SlideStructuredItemEdit,
): LocalizedSlideReview[] {
  return slides.map((slide) => {
    if (slide.slide_index !== edit.slideIndex) {
      return slide;
    }
    // AE-0430: an edit on a field mirrored from the other locale creates it.
    const presentation = editablePresentation(slide, edit.locale);
    const current = presentation[edit.listKey];
    if (!Array.isArray(current)) {
      return slide;
    }
    const nextItems = current.map((item, index) =>
      index === edit.itemIndex && item && typeof item === "object"
        ? { ...(item as Record<string, unknown>), [edit.field]: edit.value }
        : item,
    );
    return {
      ...slide,
      [edit.locale]: { ...presentation, [edit.listKey]: nextItems },
    };
  });
}

/**
 * AE-0414: free-text structured extras the content review can edit — a string
 * (``tldr_strip``, the CTA ``creator_*`` fields) or one ``title``/``body`` of an
 * object extra (``insight``). Lists use ``SlideStructuredItemEdit``.
 */
export interface SlideExtraEdit {
  slideIndex: number;
  locale: PresentationLocaleKey;
  extraKey: string;
  field?: string;
  value: string;
}

function nextExtraValue(current: unknown, edit: SlideExtraEdit): unknown {
  if (edit.field === undefined) {
    return edit.value;
  }
  if (!current || typeof current !== "object" || Array.isArray(current)) {
    return current;
  }
  return { ...(current as Record<string, unknown>), [edit.field]: edit.value };
}

export function applySlideExtraEdit(
  slides: LocalizedSlideReview[],
  edit: SlideExtraEdit,
): LocalizedSlideReview[] {
  return slides.map((slide) => {
    if (slide.slide_index !== edit.slideIndex) {
      return slide;
    }
    const presentation = editablePresentation(slide, edit.locale);
    return {
      ...slide,
      [edit.locale]: {
        ...presentation,
        [edit.extraKey]: nextExtraValue(presentation[edit.extraKey], edit),
      },
    };
  });
}

/**
 * AE-0414: a slide's full reviewable copy (both locales, every field — heading,
 * body, structured items and extras), so an edit anywhere counts as a change.
 */
function slideCopySignature(slide: LocalizedSlideReview): string {
  return JSON.stringify([slide.presentation_pt, slide.presentation_en]);
}

export function slidesHaveCopyChanges(
  original: LocalizedSlideReview[],
  edited: LocalizedSlideReview[],
): boolean {
  if (original.length !== edited.length) {
    return true;
  }
  return original.some((slide, index) => {
    const counterpart = edited[index];
    return (
      slide.slide_index !== counterpart?.slide_index ||
      slideCopySignature(slide) !== slideCopySignature(counterpart)
    );
  });
}

/**
 * AE-0414: the slides the reviewer actually changed, sent verbatim (never
 * clamped or trimmed). The backend merges edits by ``slide_index``, so an
 * untouched slide is never round-tripped and can never be overwritten.
 */
export function changedLocalizedSlides(
  original: LocalizedSlideReview[],
  edited: LocalizedSlideReview[],
): LocalizedSlideReview[] {
  const baseline = new Map(
    original.map((slide) => [slide.slide_index, slideCopySignature(slide)]),
  );
  return edited.filter(
    (slide) => baseline.get(slide.slide_index) !== slideCopySignature(slide),
  );
}

function localizedSlideLooksMalformed(slide: LocalizedSlideReview): boolean {
  const body = presentationBody(slide.presentation_pt);
  const heading = presentationHeading(slide.presentation_pt, "");
  return (
    body.trim().startsWith("{") || (body.includes("'pt'") && !heading.trim())
  );
}

function hasStructuredPresentation(
  value: unknown,
): value is Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.heading === "string" ||
    typeof record.body === "string" ||
    Array.isArray(record.summary_points) ||
    Array.isArray(record.features) ||
    Array.isArray(record.actions)
  );
}

type SlideDraft = EditorialWorkflowState["slide_drafts"][number];

function draftSlideIndex(slide: SlideDraft, position: number): number {
  return typeof slide.slide_index === "number"
    ? slide.slide_index
    : position + 1;
}

function draftSlideType(slide: SlideDraft): string {
  if (typeof slide.slide_type === "string") {
    return slide.slide_type;
  }
  return typeof slide.type === "string" ? slide.type : "content";
}

function firstString(...values: unknown[]): string {
  const found = values.find((value) => typeof value === "string");
  return typeof found === "string" ? found : "";
}

/** A draft's legacy flat copy (``heading``/``title`` + ``body``/``draft_text``). */
function legacyDraftPresentation(
  slide: SlideDraft,
  slideType: string,
): Record<string, unknown> {
  return {
    slide_type: slideType,
    heading: firstString(slide.heading, slide.title),
    body: firstString(slide.body, slide.draft_text),
  };
}

function slideFromDraft(
  slide: SlideDraft,
  position: number,
): LocalizedSlideReview {
  const slideType = draftSlideType(slide);
  const legacy = legacyDraftPresentation(slide, slideType);
  return {
    slide_index: draftSlideIndex(slide, position),
    slide_type: slideType,
    presentation_pt: hasStructuredPresentation(slide.presentation_pt)
      ? slide.presentation_pt
      : legacy,
    presentation_en: hasStructuredPresentation(slide.presentation_en)
      ? slide.presentation_en
      : legacy,
  };
}

/**
 * AE-0414 (B10): every slide of the deck, resolved PER SLIDE INDEX.
 *
 * ``state.localized_slides`` is the copy the validator checks (violations point
 * at it), the repair endpoint rewrites and manual edits merge into, so it wins
 * for each slide it carries in good shape. A slide missing from it, or whose
 * localized copy is malformed (raw JSON body), falls back to its draft
 * (structured ``presentation_*`` per locale, else the legacy flat copy). A
 * draft without presentations no longer drops its slide from the editor.
 */
export function resolveLocalizedSlides(
  state: EditorialWorkflowState,
): LocalizedSlideReview[] {
  const bySlide = new Map<number, LocalizedSlideReview>();
  state.slide_drafts.forEach((slide, position) => {
    const resolved = slideFromDraft(slide, position);
    bySlide.set(resolved.slide_index, resolved);
  });
  for (const slide of state.localized_slides ?? []) {
    // A malformed localized slide only yields to a draft that exists; it is
    // still shown (never dropped) when it is the slide's only source.
    if (
      !localizedSlideLooksMalformed(slide) ||
      !bySlide.has(slide.slide_index)
    ) {
      bySlide.set(slide.slide_index, slide);
    }
  }
  return [...bySlide.values()].sort(
    (left, right) => left.slide_index - right.slide_index,
  );
}
