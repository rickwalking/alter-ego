"use client";

import { useTranslations } from "next-intl";
import { RUBRIC_CONTENT_TYPES, SCORING_SCALES } from "@/schemas/rubric";

/** A translator of a closed set of keys; an unknown stored key shows as is. */
function useKeyLabel(
  namespace: "rubrics.contentType" | "rubrics.scoringScale",
  known: readonly string[],
): (key: string) => string {
  const t = useTranslations(namespace);
  return (key) => (known.includes(key) ? t(key) : key);
}

/** Translated label of a content type ("carousel" → "Carrossel"). */
export function useContentTypeLabel(): (type: string) => string {
  return useKeyLabel("rubrics.contentType", RUBRIC_CONTENT_TYPES);
}

/** Translated label of a scoring scale ("pass_fail" → "Aprovado / reprovado"). */
export function useScoringScaleLabel(): (scale: string) => string {
  return useKeyLabel("rubrics.scoringScale", SCORING_SCALES);
}
