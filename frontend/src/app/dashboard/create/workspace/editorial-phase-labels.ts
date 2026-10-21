"use client";

/**
 * Human phase names instead of raw phase ids, and the phase
 * an approval starts. Phase names live under `create.phases`.
 */

import { useCallback } from "react";
import { useTranslations } from "next-intl";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";

const EDITORIAL_PHASE_ORDER: readonly string[] = [
  EDITORIAL_PHASES.RESEARCH,
  EDITORIAL_PHASES.OUTLINE,
  EDITORIAL_PHASES.CONTENT,
  EDITORIAL_PHASES.DESIGN,
  EDITORIAL_PHASES.IMAGES,
  EDITORIAL_PHASES.FINAL_REVIEW,
  EDITORIAL_PHASES.PUBLISHED,
];

/** The phase an approval of `phase` runs next; the phase itself when last/unknown. */
export function nextEditorialPhase(phase: string): string {
  const index = EDITORIAL_PHASE_ORDER.indexOf(phase);
  if (index < 0) {
    return phase;
  }
  return EDITORIAL_PHASE_ORDER[index + 1] ?? phase;
}

/** Translate a phase id ("final_review") to its name; unknown ids pass through. */
export function usePhaseLabel(): (phase: string | null | undefined) => string {
  const t = useTranslations("create.phases");
  return useCallback(
    (phase: string | null | undefined): string => {
      if (!phase) {
        return "—";
      }
      return EDITORIAL_PHASE_ORDER.includes(phase) ? t(phase) : phase;
    },
    [t],
  );
}
