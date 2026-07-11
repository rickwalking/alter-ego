import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
} from "@/modules/editorial/workspace/types-ai";
import {
  presentationBody,
  presentationHeading,
} from "./presentation-review-utils";

export type PresentationLocaleKey = "presentation_pt" | "presentation_en";
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

export function applySlideStructuredItemEdit(
  slides: LocalizedSlideReview[],
  edit: SlideStructuredItemEdit,
): LocalizedSlideReview[] {
  return slides.map((slide) => {
    if (slide.slide_index !== edit.slideIndex) {
      return slide;
    }
    const presentation = slide[edit.locale];
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

function localeCopySignature(presentation: Record<string, unknown>): string {
  const heading =
    typeof presentation.heading === "string" ? presentation.heading : "";
  const body = typeof presentation.body === "string" ? presentation.body : "";
  return `${heading}\u0000${body}`;
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
    if (slide.slide_index !== counterpart.slide_index) {
      return true;
    }
    return (
      localeCopySignature(slide.presentation_pt) !==
        localeCopySignature(counterpart.presentation_pt) ||
      localeCopySignature(slide.presentation_en) !==
        localeCopySignature(counterpart.presentation_en)
    );
  });
}

function localizedSlidesLookMalformed(slides: LocalizedSlideReview[]): boolean {
  return slides.some((slide) => {
    const body = presentationBody(slide.presentation_pt);
    const heading = presentationHeading(slide.presentation_pt, "");
    return (
      body.trim().startsWith("{") || (body.includes("'pt'") && !heading.trim())
    );
  });
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

function localizedSlidesFromDraftPresentations(
  state: EditorialWorkflowState,
): LocalizedSlideReview[] {
  return state.slide_drafts.flatMap((slide, index) => {
    if (
      !hasStructuredPresentation(slide.presentation_pt) ||
      !hasStructuredPresentation(slide.presentation_en)
    ) {
      return [];
    }
    const presentationPt = slide.presentation_pt;
    const presentationEn = slide.presentation_en;
    const slideIndex =
      typeof slide.slide_index === "number" ? slide.slide_index : index + 1;
    const slideType =
      typeof slide.slide_type === "string"
        ? slide.slide_type
        : typeof slide.type === "string"
          ? slide.type
          : "content";
    return [
      {
        slide_index: slideIndex,
        slide_type: slideType,
        presentation_pt: presentationPt,
        presentation_en: presentationEn,
      },
    ];
  });
}

export function resolveLocalizedSlides(
  state: EditorialWorkflowState,
): LocalizedSlideReview[] {
  const fromDraftPresentations = localizedSlidesFromDraftPresentations(state);
  if (fromDraftPresentations.length > 0) {
    return fromDraftPresentations;
  }
  if (
    state.localized_slides &&
    state.localized_slides.length > 0 &&
    !localizedSlidesLookMalformed(state.localized_slides)
  ) {
    return state.localized_slides;
  }
  return state.slide_drafts.map((slide, index) => {
    const slideIndex =
      typeof slide.slide_index === "number" ? slide.slide_index : index + 1;
    const slideType =
      typeof slide.slide_type === "string"
        ? slide.slide_type
        : typeof slide.type === "string"
          ? slide.type
          : "content";
    const heading =
      typeof slide.heading === "string"
        ? slide.heading
        : typeof slide.title === "string"
          ? slide.title
          : "";
    const body =
      typeof slide.body === "string"
        ? slide.body
        : typeof slide.draft_text === "string"
          ? slide.draft_text
          : "";
    const presentation = {
      slide_type: slideType,
      heading,
      body,
    };
    return {
      slide_index: slideIndex,
      slide_type: slideType,
      presentation_pt: presentation,
      presentation_en: presentation,
    };
  });
}
