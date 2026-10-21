"use client";

import { useEffect, useRef } from "react";

import type {
  LocalizedSlideReview,
  SlideValidationViolation,
} from "@/modules/publishing";
import { buildSlideFieldErrors, focusInvalidField } from "@/modules/editorial";
import { CONTENT_REVIEW_ID_PREFIX } from "./content-phase-locale-fields";
import type { ContentManualFixesActions } from "./content-phase-manual-fixes";

/**
 * Submit the changed slides as manual fixes; once that run comes
 * back (no longer in progress), jump to the first field still invalid (a DOM
 * focus, not data fetching). Returns the submit callback.
 */
export function useManualFixSubmission(
  manualFixes: ContentManualFixesActions | undefined,
  {
    addressed,
    runInProgress,
    changedSlides,
  }: {
    addressed: SlideValidationViolation[];
    runInProgress: boolean;
    changedSlides: () => LocalizedSlideReview[];
  },
): () => void {
  const awaitingResult = useRef(false);
  useEffect(() => {
    if (!awaitingResult.current || runInProgress) {
      return;
    }
    awaitingResult.current = false;
    focusInvalidField(
      CONTENT_REVIEW_ID_PREFIX,
      buildSlideFieldErrors(addressed),
    );
  }, [addressed, runInProgress]);

  return (): void => {
    if (!manualFixes) {
      return;
    }
    awaitingResult.current = true;
    manualFixes.onSubmit(changedSlides());
  };
}
