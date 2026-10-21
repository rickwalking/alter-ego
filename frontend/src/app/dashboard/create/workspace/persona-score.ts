/**
 * AE-0415 (B01): persona voice scores on one 0-100 scale in the create flow.
 *
 * Mirrors the backend helper `rag_backend/domain/persona_score.py` (AE-0407):
 * a stored `overall` in (0, 10] is a 0-10 answer and reads x10; a 0, a
 * missing or a non-numeric `overall` is a failed judge call — unscored, never
 * low — and is ignored by the content-approval gate.
 */

import { PERSONA_VOICE_MATCH_MIN_SCORE } from "@/constants/editorial-workflow";

const PERSONA_SCORE_TEN_POINT_MAX = 10;
const PERSONA_SCORE_TEN_TO_HUNDRED = 10;
const PERSONA_SCORE_OVERALL_KEY = "overall";
const DIGIT_PATTERN = /^\d$/;

/** One slide whose voice score is under the approval threshold. */
export interface PersonaScoreShortfall {
  /** The `persona_scores` key, e.g. `slide_2`. */
  key: string;
  /** 1-based slide number parsed from the key, or null when the key has none. */
  slideNumber: number | null;
  /** The score on the 0-100 scale, rounded. */
  score: number;
}

/** A score in (0, 10] is a 0-10 answer: x10. Anything else is kept. */
function onHundredScale(value: number): number {
  if (value > 0 && value <= PERSONA_SCORE_TEN_POINT_MAX) {
    return value * PERSONA_SCORE_TEN_TO_HUNDRED;
  }
  return value;
}

function rawOverall(entry: unknown): unknown {
  if (entry !== null && typeof entry === "object") {
    return (entry as Record<string, unknown>)[PERSONA_SCORE_OVERALL_KEY];
  }
  return entry;
}

/** One stored entry's overall on 0-100; null when unscored. */
function storedOverall(entry: unknown): number | null {
  const raw = rawOverall(entry);
  if (typeof raw !== "number" || Number.isNaN(raw) || raw <= 0) {
    return null;
  }
  return onHundredScale(raw);
}

function slideNumberOf(key: string): number | null {
  const trimmed = key.trimEnd();
  let start = trimmed.length;
  while (start > 0 && DIGIT_PATTERN.test(trimmed.charAt(start - 1))) {
    start -= 1;
  }
  return start < trimmed.length ? Number(trimmed.slice(start)) : null;
}

/** Slides scored below the threshold, in slide order. Unscored slides are skipped. */
export function personaScoreShortfalls(
  scores: Record<string, unknown> | null | undefined,
  threshold: number = PERSONA_VOICE_MATCH_MIN_SCORE,
): PersonaScoreShortfall[] {
  if (!scores) {
    return [];
  }
  const shortfalls: PersonaScoreShortfall[] = [];
  for (const [key, entry] of Object.entries(scores)) {
    const score = storedOverall(entry);
    if (score !== null && score < threshold) {
      shortfalls.push({
        key,
        slideNumber: slideNumberOf(key),
        score: Math.round(score),
      });
    }
  }
  return shortfalls.sort((a, b) => (a.slideNumber ?? 0) - (b.slideNumber ?? 0));
}
