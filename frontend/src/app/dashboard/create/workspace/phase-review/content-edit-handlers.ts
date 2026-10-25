"use client";

import {
  applySlideCopyEdit,
  applySlideExtraEdit,
  applySlideStructuredItemEdit,
  applySlideStructuredListEdit,
  fieldErrorKey,
  listFieldErrorKeys,
  structuredItemFieldPath,
  type SlideCopyEdit,
  type SlideExtraEdit,
  type SlideStructuredItemEdit,
  type SlideStructuredListEdit,
} from "@/modules/editorial";
import type { LocalizedSlideReview } from "@/modules/publishing";

interface ContentEditHandlers {
  onCopyChange: (edit: SlideCopyEdit) => void;
  onStructuredItemChange: (edit: SlideStructuredItemEdit) => void;
  onStructuredListChange: (edit: SlideStructuredListEdit) => void;
  onExtraChange: (edit: SlideExtraEdit) => void;
}

/**
 * The content-review edit handlers: apply the edit to the slides and clear
 * the edited field's error. Structured items and free-text
 * extras are editable; list slots are added/removed (PT and EN), which clears
 * the list-level error (too few items) of both locales.
 */
export function contentEditHandlers(
  slides: LocalizedSlideReview[],
  onSlidesChange: (slides: LocalizedSlideReview[]) => void,
  clearField: (key: string) => void,
): ContentEditHandlers {
  return {
    onCopyChange: (edit) => {
      onSlidesChange(applySlideCopyEdit(slides, edit));
      clearField(fieldErrorKey(edit.slideIndex, edit.locale, edit.field));
    },
    onStructuredItemChange: (edit) => {
      onSlidesChange(applySlideStructuredItemEdit(slides, edit));
      clearField(
        fieldErrorKey(
          edit.slideIndex,
          edit.locale,
          structuredItemFieldPath(edit.listKey, edit.itemIndex, edit.field),
        ),
      );
    },
    onStructuredListChange: (edit) => {
      onSlidesChange(applySlideStructuredListEdit(slides, edit));
      listFieldErrorKeys(edit.slideIndex, edit.listKey).forEach(clearField);
    },
    onExtraChange: (edit) => {
      onSlidesChange(applySlideExtraEdit(slides, edit));
      const path = edit.field
        ? `${edit.extraKey}.${edit.field}`
        : edit.extraKey;
      clearField(fieldErrorKey(edit.slideIndex, edit.locale, path));
    },
  };
}
