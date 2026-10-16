import { useCallback, useState } from "react";
import {
  buildSlideFieldErrors,
  invalidSlideIndexes,
  openBlockingViolations,
} from "@/modules/editorial/workspace/lib/slide-field-errors";
import type { SlideValidationViolation } from "@/modules/editorial/workspace/types-ai";
import type { SlideFieldErrorState } from "./types";

/**
 * AE-0403: the per-field error state of a review form. ``validationStamp``
 * identifies one validation run: when it changes, every field's error comes
 * back (even if the new violations equal the old ones); a re-render or a state
 * poll with the same stamp keeps the fields the owner already edited cleared.
 */
export function useSlideFieldErrors(
  violations: SlideValidationViolation[],
  validationStamp: string,
): SlideFieldErrorState {
  const [stamp, setStamp] = useState(validationStamp);
  const [cleared, setCleared] = useState<ReadonlySet<string>>(new Set());
  if (stamp !== validationStamp) {
    setStamp(validationStamp);
    setCleared(new Set());
  }
  const clearField = useCallback((key: string) => {
    setCleared((current) =>
      current.has(key) ? current : new Set([...current, key]),
    );
  }, []);
  const open = openBlockingViolations(violations, cleared);
  return {
    open,
    fieldErrors: buildSlideFieldErrors(open),
    slideIndexes: invalidSlideIndexes(open),
    clearField,
  };
}
